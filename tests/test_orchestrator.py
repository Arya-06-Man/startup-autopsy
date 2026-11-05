import httpx
from autopsy.api import Crustdata
from autopsy.config import Settings
from autopsy.storage import Store
from autopsy.orchestrator import investigate
from autopsy.llm import Planner


def response():
    return [{'matches':[{'company_data':{'crustdata_company_id':1,'basic_info':{'name':'Synthetic Acme','primary_domain':'acme.test'},'headcount':{'timeseries':[]}}}]}]


def test_end_to_end_partial(tmp_path):
    def respond(req):
        if req.url.path=='/web/search/live': return httpx.Response(200,json={'success':True,'results':[]})
        if b'unknown' in req.content: return httpx.Response(200,json=[{'matches':[]}])
        return httpx.Response(200,json=response())
    store=Store(tmp_path); api=Crustdata(Settings(api_key='test'),store,httpx.MockTransport(respond))
    run=investigate(['acme.test','unknown.test'],api,store)
    assert run.status=='partial'
    assert run.companies[0].status=='complete'
    assert run.companies[1].status=='failed'
    assert run.companies[0].assessment.score is None
    assert [t['stage'] for t in run.companies[0].trace][-1]=='DELIVER'
    assert store.runs()[0].status=='partial'
    assert 'Subject:' in run.companies[0].advice['email']


def test_llm_failure_fallback(tmp_path):
    settings=Settings(gemini_key='test')
    planner=Planner(settings,httpx.MockTransport(lambda r:httpx.Response(200,json={'models':[]})))
    from autopsy.models import Dossier
    assert planner.plan(Dossier(query='x')) is None
    assert planner.error


def test_llm_rejects_unsupported_references():
    def respond(r):
        if r.method=='GET': return httpx.Response(200,json={'models':[{'name':'models/test-flash','supportedGenerationMethods':['generateContent']}]})
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"focus":"business","hypotheses":[{"explanation":"claim","alternative":"benign","evidence_ids":["fake"]}]}'}]}}]})
    from autopsy.models import Dossier
    p=Planner(Settings(gemini_key='test'),httpx.MockTransport(respond))
    assert p.plan(Dossier(query='x')) is None
    assert p.error


def test_evidence_driven_followup_fetch_and_duplicate(tmp_path):
    from datetime import date,timedelta
    import json
    queries=[]
    dates=[(date.today()-timedelta(days=n)).isoformat() for n in (100,10)]
    def respond(req):
        body=json.loads(req.content)
        if req.url.path=='/web/search/live':
            queries.append(body['query'])
            return httpx.Response(200,json={'success':True,'results':[{'url':'https://example.test/article','title':'Synthetic source','snippet':'Synthetic test only'}]})
        if req.url.path=='/web/enrich/live':
            return httpx.Response(200,json=[{'success':True,'url':'https://example.test/article','title':'Synthetic source','content':'<html><script>ignored</script><p>Synthetic source content.</p></html>'}])
        data=response()
        c=data[0]['matches'][0]['company_data']
        c['headcount']={'timeseries':[{'date':dt,'employee_count':v} for dt,v in zip(dates,(100,20))]}
        c['hiring']={'open_jobs_timeseries':[{'date':dt,'open_jobs':v} for dt,v in zip(dates,(10,10))]}
        return httpx.Response(200,json=data)
    store=Store(tmp_path); api=Crustdata(Settings(api_key='test'),store,httpx.MockTransport(respond))
    run=investigate(['acme.test','Synthetic Acme'],api,store)
    assert 'workforce layoffs' in queries[0]
    assert run.companies[1].status=='duplicate'
    articles=[e for e in run.companies[0].evidence if e.category=='article']
    assert articles and 'ignored' not in articles[0].value['text']
    assert articles[0].status=='single-source observation'
    assert len(queries)<=2


def test_malformed_llm_output():
    from autopsy.models import Dossier
    def respond(r):
        if r.method=='GET': return httpx.Response(200,json={'models':[{'name':'models/test-flash','supportedGenerationMethods':['generateContent']}]})
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'not json'}]}}]})
    p=Planner(Settings(gemini_key='test'),httpx.MockTransport(respond))
    assert p.plan(Dossier(query='x')) is None
    assert p.error


def test_blocked_fetch_is_not_article(tmp_path):
    from autopsy.research import fetch_lead
    from autopsy.models import Dossier,Evidence
    def respond(r): return httpx.Response(200,json=[{'success':True,'url':'https://example.test/a','title':'Page Unavailable','content':'<h1>Page Unavailable</h1>'}])
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(respond))
    d=Dossier(query='test',company_id='1')
    fetch_lead(api,d,[Evidence(company_id='1',category='research_lead',fact='x',value={},source='https://example.test/a')])
    assert d.errors
    assert d.evidence[0].category=='fetch_error'
    assert d.evidence[0].status=='unknown'
