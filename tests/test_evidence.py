import pytest
from autopsy.evidence import normalize_company,normalize_search,verify,validate_refs
from autopsy.models import Evidence


def test_normalization():
    c={'crustdata_company_id':1,'headcount':{'total':10,'timeseries':[{'date':'2026-01-01','employee_count':12},{'date':'bad','employee_count':7}]},'hiring':{'open_jobs_timeseries':[{'date':'2026-02-01','open_jobs':0}]}}
    items=normalize_company(c,{'endpoint':'/company/enrich','retrieved_at':'2026-03-01T00:00:00+00:00'})
    assert len(items)==3
    assert items[1].event_date is None
    assert all(e.status=='single-source observation' for e in items)


def test_conflicts_and_duplicate_sources():
    a=Evidence(company_id='1',category='workforce',fact='count',value=10,source='https://a.com/x',event_date='2026-01-01')
    b=a.model_copy(update={'id':'E-b','value':20,'source':'https://b.com/x'})
    items=verify([a,a,b])
    assert len(items)==2
    assert all(e.status=='disputed/conflicting' for e in items)
    assert b.id in a.conflicts


def test_references():
    with pytest.raises(ValueError): validate_refs(['invented'],[])


def test_search_is_not_fact():
    result={'data':{'results':[{'url':'https://news.com/a','title':'A claim','snippet':'something'}]},'retrieved_at':'2026-01-01T00:00:00Z'}
    assert normalize_search(result,'1')[0].status=='unknown'
