import json
from datetime import date,timedelta
import httpx
import pytest
from autopsy.api import Crustdata,ResearchError
from autopsy.identity import identify_company,IdentityError
from autopsy.config import Settings
from autopsy.storage import Store
from autopsy.orchestrator import investigate
from autopsy.llm import Planner
from autopsy.models import Evidence,Dossier
from autopsy.evidence import normalize_company,verify
from autopsy.health import company_health
from autopsy.risk import assess


def record(domain='synthetic.test',cid=1,name='Synthetic',aliases=None):
    return [{'matches':[{'confidence_score':.9,'company_data':{'crustdata_company_id':cid,
        'basic_info':{'name':name,'primary_domain':domain,'all_domains':aliases or []}}}]}]


def test_exact_first_and_secondary_requires_domain_proof(tmp_path):
    seen=[]
    def respond(req):
        body=json.loads(req.content); seen.append(body)
        return httpx.Response(200,json=[] if 'domains' in body else record())
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(respond))
    company,result,method=identify_company(api,'synthetic.test')
    assert company['crustdata_company_id']==1 and 'corroborated' in method
    assert seen[0]['exact_match'] is True and seen[1]['exact_match'] is False
    assert api.calls==2


def test_uncertain_name_not_silently_selected(tmp_path):
    def respond(req): return httpx.Response(200,json=record(domain='different.test'))
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(respond))
    with pytest.raises(IdentityError) as error: identify_company(api,'synthetic.test')
    assert error.value.options[0]['domain']=='different.test'
    assert error.value.options[0]['confidence']==.9
    assert 'no company was selected' in str(error.value)


def test_documented_alias_and_manual_id_revalidation(tmp_path):
    def respond(req): return httpx.Response(200,json=record(aliases=['alias.test']))
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(respond))
    assert identify_company(api,'alias.test')[0]['crustdata_company_id']==1
    assert identify_company(api,'unresolved.test',{'company_id':'1','domain':'synthetic.test'})[0]['crustdata_company_id']==1
    with pytest.raises(IdentityError): identify_company(api,'unresolved.test',{'company_id':'2','domain':'synthetic.test'})


def test_refresh_bypasses_cache_without_rewriting_history(tmp_path):
    settings=Settings(api_key='test'); store=Store(tmp_path)
    api=Crustdata(settings,store,httpx.MockTransport(lambda req:httpx.Response(200,json=record())))
    first=api.identify('synthetic.test')
    assert api.identify('synthetic.test')['retrieved_at']==first['retrieved_at'] and api.calls==1
    settings.refresh_data=True
    assert api.identify('synthetic.test')['mode']=='LIVE DATA' and api.calls==2


def test_failed_live_attempt_does_not_turn_cached_evidence_into_live_data(tmp_path):
    store=Store(tmp_path)
    from autopsy.models import now
    payload={'domains':['synthetic.test'],'exact_match':True,'fields':['basic_info']}
    store.put_cache('/company/identify',payload,{'data':record(),'endpoint':'/company/identify','mode':'LIVE DATA','retrieved_at':now()})
    api=Crustdata(Settings(api_key='test',max_iterations=0),store,httpx.MockTransport(lambda req:httpx.Response(403)))
    run=investigate(['synthetic.test'],api,store)
    assert run.status=='partial' and api.calls==1 and api.cache_hits==1
    assert run.mode=='CACHED REAL DATA'
    assert {e.data_mode for e in run.companies[0].evidence}=={'CACHED REAL DATA'}


def test_all_failed_is_failed_and_history_preserved(tmp_path):
    store=Store(tmp_path)
    api=Crustdata(Settings(api_key='test'),store,httpx.MockTransport(lambda req:httpx.Response(200,json=[])))
    run=investigate(['unknown.test'],api,store)
    assert run.status=='failed' and run.companies[0].status=='failed'
    assert run.usage['incomplete_reasons'] and store.runs()[0].id==run.id


def test_missing_optional_data_and_llm_do_not_fail_execution(tmp_path):
    def respond(req):
        if req.url.path.startswith('/web/'): return httpx.Response(200,json={'results':[]})
        return httpx.Response(200,json=record(domain=None,name=None,aliases=['synthetic.test']))
    store=Store(tmp_path)
    api=Crustdata(Settings(api_key='test',max_iterations=0),store,httpx.MockTransport(respond))
    planner=Planner(Settings(gemini_key='test'),httpx.MockTransport(lambda req:httpx.Response(401)))
    run=investigate(['synthetic.test'],api,store,planner)
    d=run.companies[0]
    assert run.status=='complete' and not d.errors and d.assessment.coverage==0
    assert d.name==d.query and d.domain==d.query and store.runs()[0].id==run.id
    assert d.metadata['llm_diagnostics']['status']=='FALLBACK'
    assert 'identity_resolution' not in d.evidence[0].value  # No derived fields in raw provider observations.
    assert company_health(d)['verification']=='Single-source; independently unverified'


def test_dates_are_separate_and_new_counts_still_score():
    dates=[(date.today()-timedelta(days=n)).isoformat() for n in (100,10)]
    company={'crustdata_company_id':1,'updated_at':'2026-11-01T00:00:00Z',
        'headcount':{'timeseries':[{'date':d,'employee_count':v} for d,v in zip(dates,(100,50))]},
        'hiring':{'open_jobs_timeseries':[{'date':d,'open_jobs':v} for d,v in zip(dates,(10,5))]},
        'news':[{'article_url':'https://example.test/news','article_title':'Synthetic headline','article_publish_date':'2026-10-01'}]}
    evidence=normalize_company(company,{'endpoint':'/company/enrich','mode':'CACHED REAL DATA','retrieved_at':'2026-11-02T00:00:00Z'})
    assert evidence[0].event_date is None and evidence[0].observation_date==dates[0]
    assert evidence[0].provider_updated_at=='2026-11-01T00:00:00Z' and evidence[0].data_mode=='CACHED REAL DATA'
    assert assess(evidence).coverage==55
    news=next(e for e in evidence if e.category=='news_observation')
    assert news.publication_date=='2026-10-01' and news.event_date is None
    other=evidence[0].model_copy(update={'id':'E-other','value':80})
    assert verify([evidence[0],other])[0].status=='disputed/conflicting'


@pytest.mark.parametrize('body',[{},[None],[{'matches':[None]}],[{'matches':[{'company_data':'bad'}]}]])
def test_bad_identity_shapes_are_actionable(body,tmp_path):
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(lambda req:httpx.Response(200,json=body)))
    with pytest.raises(ResearchError): identify_company(api,'synthetic.test')
