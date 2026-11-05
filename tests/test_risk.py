from datetime import date
import pytest
from autopsy.models import Evidence
from autopsy.risk import assess,trend,runway


def rows(category,values=(100,70)):
    return [Evidence(company_id='1',category=category,fact='count',value=n,source='api',event_date=d) for d,n in zip(['2026-06-01','2026-09-01'],values)]


def test_calculation():
    a=assess(rows('workforce')+rows('hiring',(10,5)),as_of=date(2026,10,1))
    assert a.score==100
    assert a.coverage==55
    assert a.label=='Urgent review'
    assert len(a.missing)==2


def test_missing_never_safe():
    assert assess([]).score is None
    assert assess(rows('workforce'),as_of=date(2026,10,1)).score is None
    assert trend(rows('hiring',(0,5)),'hiring',date(2026,10,1)) is None
    assert trend(rows('workforce'),'workforce',date(2027,10,1)) is None


def test_conflicting_excluded():
    r=rows('workforce'); r[0].status='disputed/conflicting'
    assert trend(r,'workforce',date(2026,10,1)) is None


def test_financial_safeguards():
    assert runway(100,10,'2026-01-01')==10
    with pytest.raises(ValueError): runway(100,0,'2026-01-01')
    with pytest.raises(ValueError): runway(100,10,'2099-01-01')
