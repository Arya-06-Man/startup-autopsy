import pytest
from autopsy.finance import deal_metrics,Scenario,simulate,readiness,financing_round
from autopsy.mandate import Mandate
from autopsy.portfolio import allocate
from autopsy.risk import assess,runway
from tests.test_vcos_finance import deal,dossier


def test_zero_revenue_is_actual_complete_contraction():
    out=deal_metrics(deal(revenue=0,prior_revenue=100))
    assert out['revenue_growth']==-1 and out['valuation_revenue_multiple'] is None


def test_cashflow_neutral_deal_has_no_finite_depletion_runway():
    out=deal_metrics(deal(monthly_burn=0))
    assert out['runway_months'] is None
    assert any('Zero net burn' in s for s in out['assumptions'])


def test_case_and_whitespace_cannot_bypass_sector_stage_limits():
    m=Mandate(capital=100,min_cheque=10,max_cheque=25,sector_limit=.3,stage_limit=.3)
    deals=[deal(),deal('synth-b',sector=' software ',stage='SEED')]
    out=allocate(m,deals,{d.company_id:dossier(d) for d in deals},'base')
    assert sum(out['allocations'].values())==pytest.approx(30)
    assert sum(out['sector_exposure'].values())==pytest.approx(30)
    assert len(out['sector_exposure'])==1 and len(out['stage_exposure'])==1


def test_existing_exposures_and_duplicate_ids_are_normalized():
    m=Mandate(capital=100,existing=[{'company_id':'SYNTH-A','sector':' SOFTWARE ','stage':'SEED','amount':20}])
    d=deal()
    assert 'Company concentration limit' in readiness(m,d,dossier(d))['violations']
    with pytest.raises(ValueError): allocate(m,[d,deal(' SYNTH-A ')])


def test_iso_country_and_country_name_are_equivalent_without_fx():
    m=Mandate(capital=100,geographies=['India'])
    d=deal(geography='IND')
    assert 'geography outside mandate' not in readiness(m,d,dossier(d))['violations']


def test_partial_cheques_still_respect_ownership_floor():
    m=Mandate(capital=100,min_cheque=5,max_cheque=25,sector_limit=.35,target_ownership_min=.2)
    deals=[deal(),deal('synth-b')]
    out=allocate(m,deals,{d.company_id:dossier(d) for d in deals},'base')
    assert sum(out['allocations'].values())==pytest.approx(20)
    assert all(v<1e-7 or v>=20-1e-7 for v in out['allocations'].values())


@pytest.mark.parametrize('operation',[
    lambda:deal_metrics(deal(valuation=1e308,round_size=1e308)),
    lambda:simulate(Scenario(cash=1e308,monthly_burn=0,monthly_revenue=1e308,monthly_revenue_growth=1)),
    lambda:financing_round(.2,1e308,1e308),
    lambda:runway(1e308,1e-308,'2026-01-01'),
    lambda:assess([],weights={'workforce':float('nan'),'leadership':.3,'hiring':.2,'business':.15})])
def test_overflow_and_nonfinite_weights_rejected(operation):
    with pytest.raises(ValueError): operation()
