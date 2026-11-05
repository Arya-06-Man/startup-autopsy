import pytest
from autopsy.committee import context
from autopsy.mandate import Mandate
from autopsy.portfolio import allocate
from autopsy.vcos_reports import export
from tests.test_vcos_finance import deal,dossier


def memo():
    m=Mandate(capital=100); d=deal(); dossiers={d.company_id:dossier(d)}
    return context(m,[d],dossiers,allocate(m,[d],dossiers,'base'))


def test_dashboard_calculations_and_sources_are_revalidated():
    ctx=memo()
    result=export(ctx)
    assert 'Executive investment summary' in result['html']
    assert 'Side-by-side comparison' in result['md']
    assert 'href="https://example.test"' in result['html']
    ctx['deals'][0]['metrics']['ownership']=.99
    with pytest.raises(ValueError,match='Stale financial'): export(ctx)


def test_memo_rejects_source_and_terms_reference_substitution():
    ctx=memo(); key=next(k for k in ctx['references'] if k.startswith('E-'))
    ctx['references'][key]['source']='https://fabricated.test'
    with pytest.raises(ValueError,match='original company ledger'): export(ctx)
    ctx=memo(); ctx['references']['A-synth-a']['value']['investment']=50
    with pytest.raises(ValueError,match='Terms reference'): export(ctx)


def test_memo_cannot_publish_infeasible_allocation():
    ctx=memo(); ctx['allocation']['allocations']['synth-a']=30; ctx['allocation']['uninvested']=40
    with pytest.raises(ValueError,match='exposure'): export(ctx)
    ctx=memo(); ctx['allocation']['reserve']=0
    with pytest.raises(ValueError,match='reconcile'): export(ctx)


def test_regenerated_report_reflects_actual_changed_terms():
    first=memo(); d=deal(valuation=180); m=Mandate(capital=100); ds={d.company_id:dossier(d)}
    second=context(m,[d],ds,allocate(m,[d],ds,'base'))
    assert first['deals'][0]['metrics']['ownership']==.2
    assert second['deals'][0]['metrics']['ownership']==.1
    assert export(first)['json']!=export(second)['json']
