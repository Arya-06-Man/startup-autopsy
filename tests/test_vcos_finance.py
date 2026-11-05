from datetime import date
import pytest
from autopsy.finance import Deal,Scenario,deal_metrics,simulate,financing_round,readiness
from autopsy.mandate import Mandate
from autopsy.models import Dossier,Evidence
from autopsy.portfolio import allocate,stress


def deal(cid='synth-a',**updates):
    return Deal(**({'company_id':cid,'name':'Synthetic '+cid,'investment':20,'valuation':80,
        'round_size':20,'sector':'Software','stage':'seed','geography':'India',
        'cash':100,'monthly_burn':10,'revenue':50,'financial_date':date.today(),
        'documents':['Financial statements','Cap table','Term sheet'],
        'downside_moic':1.1,'base_moic':2,'upside_moic':4,'provenance':'SYNTHETIC DEMO DATA'}|updates))


def dossier(d):
    return Dossier(query=d.name,company_id=d.company_id,status='complete',evidence=[Evidence(company_id=d.company_id,
        category='identity',fact='Synthetic fixture',value=d.name,source='https://example.test')])


def test_financial_metrics():
    d=deal(prior_revenue=25,gross_profit=40,operating_profit=-10)
    m=deal_metrics(d)
    assert m['post_money']==100 and m['ownership']==.2 and m['valuation_revenue_multiple']==2
    assert m['runway_months']==10 and m['revenue_growth']==1
    assert m['gross_margin']==.8 and m['operating_margin']==-.2
    assert deal_metrics(deal(valuation=100,valuation_basis='post-money'))['ownership']==.2


@pytest.mark.parametrize('instrument',['SAFE','Convertible note','Preferred shares'])
def test_incompatible_instruments_withhold_math(instrument):
    m=deal_metrics(deal(instrument=instrument))
    assert m['post_money'] is None and m['ownership'] is None


@pytest.mark.parametrize('updates',[{'round_size':10},{'valuation_basis':'post-money','valuation':10},
    {'investment':float('inf')},{'cash':-1},{'monthly_burn':-1},{'downside_moic':-1}])
def test_invalid_terms(updates):
    with pytest.raises(ValueError): deal(**updates)


def test_readiness_and_missing_data():
    m=Mandate(capital=100,min_cheque=5,max_cheque=25,company_limit=.25,sector_limit=.6,stage_limit=.8)
    d=deal()
    assert readiness(m,d,dossier(d))['status']=='CONDITIONALLY REVIEWABLE'
    assert readiness(m,deal(human_review_confirmed=True),dossier(d))['status']=='READY FOR COMMITTEE REVIEW'
    assert readiness(m,deal(cash=None),dossier(d))['status']=='MORE DILIGENCE REQUIRED'
    assert readiness(m,deal(investment=30,round_size=30),dossier(d))['status']=='OUTSIDE MANDATE'
    assert readiness(m,d)['status']=='MORE DILIGENCE REQUIRED'


def test_runway_cash_exhaustion_and_funding_delay():
    s=Scenario(cash=100,monthly_burn=10,ownership=.2,invested=20,exit_value=1000)
    assert simulate(s)['cash_exhaustion_month']==10
    late=simulate(s.model_copy(update={'financing':1000,'financing_month':11,'dilution':.2}))
    assert not late['financing_received'] and late['exit_proceeds']==0 and late['moic']==0
    early=simulate(s.model_copy(update={'financing':1000,'financing_month':10,'dilution':.2}))
    assert early['financing_received'] and early['ending_ownership']==pytest.approx(.16)
    assert early['moic']==pytest.approx(8)
    assert early['annualized_return']==pytest.approx(8**.2-1)


def test_net_burn_not_double_counted_and_reductions():
    s=Scenario(cash=100,monthly_burn=10,monthly_revenue=100)
    assert simulate(s)['cash_exhaustion_month']==10
    assert simulate(s.model_copy(update={'burn_reduction':.5}))['cash_exhaustion_month']==20
    assert simulate(s.model_copy(update={'implementation_cost':100}))['cash_exhaustion_month']==0
    assert simulate(Scenario(cash=100,monthly_burn=0))['baseline_runway_months'] is None
    assert simulate(s.model_copy(update={'invested':0}))['moic'] is None


def test_cap_table_pro_rata_pool():
    out=financing_round(.2,80,20,4)
    assert out['ownership_after']==pytest.approx(.2) and out['pro_rata_capital_before_pool']==4
    assert financing_round(.2,80,20)['ownership_after']==pytest.approx(.16)
    pool=financing_round(.2,80,20,0,.1)
    assert pool['ownership_after']==pytest.approx(.144)
    maintained=financing_round(.2,80,20,pool['capital_to_maintain_after_pool'],.1)
    assert maintained['ownership_after']==pytest.approx(.2)
    with pytest.raises(ValueError): financing_round(.2,80,20,21)
    with pytest.raises(ValueError): financing_round(.2,float('nan'),20)


def test_allocation_limits_and_reserves():
    m=Mandate(capital=100,min_cheque=10,max_cheque=25,company_limit=.25,sector_limit=.35,stage_limit=.5)
    deals=[deal(),deal('synth-b')]; dossiers={d.company_id:dossier(d) for d in deals}
    out=allocate(m,deals,dossiers,'base')
    assert sum(out['allocations'].values())==pytest.approx(35)
    assert out['uninvested']==pytest.approx(35) and out['reserve']==30
    assert all(v<=25+1e-7 and (v<1e-7 or v>=10-1e-7) for v in out['allocations'].values())
    assert out['sector_exposure']['Software']==pytest.approx(35)


def test_zero_allocation_missing_and_negative_surplus():
    m=Mandate(capital=100,min_cheque=10,max_cheque=25)
    d=deal(downside_moic=0,base_moic=.8)
    assert allocate(m,[d],{d.company_id:dossier(d)})['allocations'][d.company_id]==0
    d=deal(base_moic=None)
    out=allocate(m,[d],{d.company_id:dossier(d)})
    assert out['uninvested']==70 and out['excluded']
    assert allocate(m,[deal()])['excluded']


def test_impossible_constraints_duplicates_and_existing_exposure():
    d=deal(); ds={d.company_id:dossier(d)}
    with pytest.raises(ValueError): allocate(Mandate(capital=100),[d,d],ds)
    m=Mandate(capital=100,min_cheque=21,max_cheque=25)
    assert allocate(m,[d],ds,'base')['allocations'][d.company_id]==0
    m=Mandate(capital=100,existing=[{'company_id':'synth-a','sector':'Software','stage':'seed','amount':15}]*2)
    out=allocate(m,[d],ds)
    assert out['violations'] and out['allocations'][d.company_id]==0
    assert out['sector_exposure']['Software']==30
    m=Mandate(capital=100,reserve_fraction=.95)
    assert allocate(m,[d],ds)['allocations'][d.company_id]==0


def test_stress_zero_recovery():
    out=stress({'synth-a':20},[deal()],.5,['synth-a'])
    assert out['capital_at_risk']==20 and out['proceeds']==0
