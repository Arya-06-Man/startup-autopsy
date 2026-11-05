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
