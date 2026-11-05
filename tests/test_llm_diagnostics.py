import json
import httpx
import pytest
from autopsy.config import Settings
from autopsy.diagnostics import gemini_probe
from autopsy.llm import Planner
from autopsy.models import Dossier
from autopsy.committee import context,review
from autopsy.mandate import Mandate
from tests.test_vcos_finance import deal,dossier


def test_probe_plain_structured_and_redaction():
    def respond(req):
        if req.method=='GET': return httpx.Response(200,json={'models':[{'name':'models/synthetic-flash','supportedGenerationMethods':['generateContent']}]})
        if 'responseJsonSchema' in json.loads(req.content)['generationConfig']:
            return httpx.Response(403,json={'error':{'status':'PERMISSION_DENIED','message':'credential=secret-test'}})
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'OK'}]}}]})
    result=gemini_probe(Settings(gemini_key='secret-test'),transport=httpx.MockTransport(respond))
    assert result['attempts'][1]['response_text']=='OK'
    assert result['attempts'][2]['http_status']==403
    assert 'secret-test' not in json.dumps(result)
    assert not result['structured_generation_verified']


def test_stable_model_config_bounded_output_and_thinking_parts():
    def respond(req):
        if req.method=='GET': return httpx.Response(200,json={'models':[{'name':name,'supportedGenerationMethods':['generateContent']} for name in ('models/gemini-flash-latest','models/gemini-3.8-flash','models/gemini-3.5-flash')]})
        body=json.loads(req.content)
        assert req.url.path.endswith('gemini-3.5-flash:generateContent')
        assert body['generationConfig']['maxOutputTokens']==2048
        assert body['generationConfig']['thinkingConfig']=={'thinkingLevel':'LOW'}
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'hidden reasoning','thought':True},{'text':'{"focus":'},{'text':'"stop"}'}]}}]})
    p=Planner(Settings(gemini_key='test'),httpx.MockTransport(respond))
    assert p.plan(Dossier(query='synthetic')).focus=='stop'
    assert p.diagnostics()['validated_generations']==1
    p.close()


@pytest.mark.parametrize('status',[401,403,429])
def test_provider_failure_stops_further_calls(status):
    p=Planner(Settings(gemini_key='test'),httpx.MockTransport(lambda r:httpx.Response(status,json={'error':{'status':'RESOURCE_EXHAUSTED','message':'Quota unavailable'}})))
    p.model='models/synthetic-flash'
    assert p.plan(Dossier(query='synthetic')) is None
    assert p.plan(Dossier(query='synthetic')) is None
    assert p.calls==1 and p.diagnostics()['attempts'][0]['provider_status']=='RESOURCE_EXHAUSTED'
    p.close()


def test_factual_assertion_with_valid_reference_rejected():
    d=deal(); ctx=context(Mandate(capital=100),[d],{d.company_id:dossier(d)})
    source=next(k for k in ctx['references'] if k.startswith('E-'))
    def respond(req):
        text=json.dumps({'thesis':[{'claim':'Invented audited revenue','references':[source],'kind':'observation'}],'challenges':[],'questions':[]})
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':text}]}}]})
    p=Planner(Settings(gemini_key='test'),httpx.MockTransport(respond)); p.model='models/synthetic-flash'
    assert review(ctx,p)['engine']=='DETERMINISTIC FALLBACK'
    assert p.calls==1
    p.close()
