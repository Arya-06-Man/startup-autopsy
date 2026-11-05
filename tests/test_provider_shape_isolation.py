import json
import httpx
import pytest
from autopsy.api import Crustdata
from autopsy.config import Settings
from autopsy.storage import Store
from autopsy.orchestrator import investigate
from autopsy.models import Dossier,Evidence
from autopsy.evidence import normalize_search
from autopsy.research import fetch_lead


@pytest.mark.parametrize('failure',['identity','funding'])
def test_malformed_company_cannot_interrupt_remaining_portfolio(tmp_path,failure):
    def respond(req):
        body=json.loads(req.content)
        bad='bad.test' in str(body) or body.get('crustdata_company_ids')==[1]
        cid=1 if bad else 2
        basic={'name':'Synthetic bad' if bad else 'Synthetic good','primary_domain':'bad.test' if bad else 'good.test'}
        company={'crustdata_company_id':cid,'basic_info':basic}
        if bad and failure=='identity' and req.url.path=='/company/identify': company['basic_info']='malformed'
        if bad and failure=='funding' and req.url.path=='/company/enrich': company['funding']=['malformed']
        return httpx.Response(200,json=[{'matches':[{'company_data':company}]}])
    api=Crustdata(Settings(api_key='test',max_iterations=0),Store(tmp_path),httpx.MockTransport(respond))
    run=investigate(['bad.test','good.test'],api,api.store)
    assert run.status=='partial'
    assert run.companies[0].status in ('partial','failed') and run.companies[0].errors
    assert run.companies[1].status=='complete' and run.companies[1].evidence
    assert api.store.runs()[0].companies[1].status=='complete'


def test_malformed_search_results_are_not_silent_empty_success():
    with pytest.raises(ValueError):
        normalize_search({'data':{'success':True,'results':{'not':'a list'}},'retrieved_at':'2026-01-01T00:00:00Z'},'1')


def test_malformed_fetch_row_does_not_discard_following_readable_page(tmp_path):
    url='https://example.test/readable'
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(lambda req:httpx.Response(200,json=[None,{'success':True,'url':url,'title':'Synthetic document','content':'Readable synthetic content.'}])))
    d=Dossier(query='synthetic.test',company_id='1')
    fetch_lead(api,d,[Evidence(company_id='1',category='research_lead',fact='Synthetic lead',value={},source=url)])
    assert d.errors and any(e.category=='article' for e in d.evidence)
