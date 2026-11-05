"""Small, credential-safe provider probes. No retries, company data or tool claims."""
import time
import httpx


def safe_failure(response, secret=''):
    try:
        body=response.json()
        error=body.get('error',{}) if isinstance(body,dict) else {}
        if not isinstance(error,dict): return {'http_status':response.status_code}
        message=''.join(c for c in str(error.get('message','')) if c.isprintable())
        if secret: message=message.replace(secret,'[redacted]')
        return {'http_status':response.status_code,'provider_status':str(error.get('status',''))[:80],
                'message':message[:600]}
    except (ValueError,TypeError): return {'http_status':response.status_code}


def gemini_probe(settings, model='', transport=None):
    result={'provider':'GEMINI','endpoint':'https://generativelanguage.googleapis.com/v1beta',
            'implementation':'httpx REST; Google GenAI SDK is not used','attempts':[]}
    if not settings.gemini_key:
        return {**result,'limitation':'GEMINI_API_KEY is missing'}
    with httpx.Client(base_url=result['endpoint']+'/',headers={'x-goog-api-key':settings.gemini_key},
                      timeout=httpx.Timeout(20,connect=5),transport=transport) as http:
        def call(stage,path,payload=None):
            start=time.monotonic()
            attempt={'stage':stage}
            try:
                response=http.get(path) if payload is None else http.post(path,json=payload)
                attempt['http_status']=response.status_code
                if response.is_error: attempt.update(safe_failure(response,settings.gemini_key))
                else:
                    data=response.json()
                    if stage=='discovery': return data
                    candidate=data.get('candidates',[{}])[0]
                    text=''.join(p.get('text','') for p in candidate.get('content',{}).get('parts',[]) if not p.get('thought'))
                    attempt.update(finish_reason=candidate.get('finishReason'),response_text=text[:200])
                    if stage=='structured':
                        import json
                        try: attempt['schema_valid']=json.loads(text)=={'ok':True}
                        except ValueError: attempt['schema_valid']=False
            except httpx.HTTPError as exc: attempt['error_type']=type(exc).__name__
            except (ValueError,IndexError,AttributeError,TypeError): attempt['error_type']='Invalid provider response'
            finally:
                attempt['elapsed_seconds']=round(time.monotonic()-start,2)
                result['attempts'].append(attempt)
            return None
        data=call('discovery','models')
        if not data: return result
        names=[m['name'] for m in data.get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[]) and 'flash' in m.get('name','') and not any(x in m['name'] for x in ('tts','image'))]
        result['advertised_models']=names
        chosen=(model or settings.gemini_model).removeprefix('models/')
        selected='models/'+chosen if chosen else next((m for m in names if m=='models/gemini-flash-lite-latest'),next(iter(names),''))
        result['model']=selected
        if selected not in names: return {**result,'limitation':'Requested model is not advertised for generateContent'}
        config={'maxOutputTokens':256,'temperature':0}
        if 'gemini-2.5-' in selected: config['thinkingConfig']={'thinkingBudget':0}
        elif 'gemini-3' in selected: config['thinkingConfig']={'thinkingLevel':'LOW'}
        call('plain',selected+':generateContent',{'contents':[{'role':'user','parts':[{'text':'Reply with only OK.'}]}],'generationConfig':config})
        call('structured',selected+':generateContent',{'contents':[{'role':'user','parts':[{'text':'Return {"ok":true}.'}]}],
            'generationConfig':{**config,'responseMimeType':'application/json','responseJsonSchema':{
                'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}}})
    result['structured_generation_verified']=any(a.get('schema_valid') for a in result['attempts'])
    return result
