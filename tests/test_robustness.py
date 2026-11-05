import httpx
import pytest
from autopsy.api import Crustdata,ResearchError
from autopsy.config import Settings
from autopsy.storage import Store
from autopsy.ingestion import ingest
from autopsy.evidence import safe_url,valid_date

@pytest.mark.parametrize('content',[b'company\na,extra\n', b'company\n\xff',b'wrong\na'])
def test_invalid_csv(content):
    with pytest.raises(ValueError): ingest(csv_bytes=content)

@pytest.mark.parametrize('url',['javascript:alert(1)','https://user:password@a.com','file:///etc/passwd','https://'])
def test_safe_links(url): assert not safe_url(url)


def test_budget_counts_retries_and_credit_stop(tmp_path):
    api=Crustdata(Settings(api_key='test',max_calls=2),Store(tmp_path),httpx.MockTransport(lambda r:httpx.Response(503)))
    with pytest.raises(ResearchError,match='budget'): api.search('query')
    assert api.calls==2


def test_403_credits_stops_future_calls(tmp_path):
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(lambda r:httpx.Response(403,json={'error':{'type':'insufficient_credits'}})))
    with pytest.raises(ResearchError): api.identify('a.com')
    with pytest.raises(ResearchError,match='halted'): api.identify('b.com')
    assert api.calls==1


def test_actual_credits_limit_future_calls(tmp_path):
    api=Crustdata(Settings(api_key='test',max_credits=5),Store(tmp_path),httpx.MockTransport(lambda r:httpx.Response(200,json=[],headers={'X-Credits-Used':'6'})))
    api.identify('a.com')
    with pytest.raises(ResearchError,match='budget'): api.identify('b.com')


def test_invalid_json(tmp_path):
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(lambda r:httpx.Response(200,text='not json')))
    with pytest.raises(ResearchError,match='invalid JSON'): api.identify('a.com')


def test_unknown_date(): assert valid_date('nonsense') is None
