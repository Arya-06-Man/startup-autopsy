import httpx
import pytest
from autopsy.api import Crustdata, ResearchError, resolve
from autopsy.config import Settings
from autopsy.storage import Store


def record():
    return [{'matches':[{'company_data':{'crustdata_company_id':1,'basic_info':{'name':'Acme','primary_domain':'acme.com'}}}]}]


def test_resolve():
    assert resolve(record(),'acme.com')['crustdata_company_id']==1
    with pytest.raises(ResearchError): resolve(record(),'unknown.com')
    with pytest.raises(ResearchError): resolve({},'Acme')
    data=record(); data[0]['matches'].append({'company_data':{'crustdata_company_id':2}})
    with pytest.raises(ResearchError,match='Ambiguous'): resolve(data,'Acme')

@pytest.mark.parametrize('status',[401,402,403,404,429,500])
def test_errors(tmp_path,status):
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(lambda r:httpx.Response(status)))
    with pytest.raises(ResearchError): api.identify('acme.com')
    assert api.calls == (3 if status in (429,500) else 1)
    api.close()


def test_cache_budget_and_headers(tmp_path):
    def respond(r):
        assert r.headers['x-api-version']=='2025-11-01'
        return httpx.Response(200,json=record(),headers={'X-Credits-Used':'0'})
    api=Crustdata(Settings(api_key='test',max_calls=1),Store(tmp_path),httpx.MockTransport(respond))
    assert api.identify('acme.com')['mode']=='LIVE DATA'
    assert api.identify('acme.com')['mode']=='CACHED REAL DATA'
    with pytest.raises(ResearchError,match='budget'): api.identify('other.com')


def test_timeout(tmp_path):
    def fail(r): raise httpx.ReadTimeout('timeout')
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(fail))
    with pytest.raises(ResearchError,match='three'): api.identify('acme.com')
    assert api.calls==3
