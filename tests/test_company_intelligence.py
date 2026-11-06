from datetime import date,timedelta
import pytest
from autopsy.company_intelligence import analyze,compare
from autopsy.models import Dossier,Evidence


def dossier(name,values):
    today=date(2026,11,6)
    evidence=[]
    for i,(w,h) in enumerate(values):
        day=today-timedelta(days=(len(values)-1-i)*30)
        evidence += [Evidence(company_id=name,category='workforce',fact='employee count',value=w,source='https://api.crustdata.com/company/enrich',observation_date=day.isoformat()),
                     Evidence(company_id=name,category='hiring',fact='open roles',value=h,source='https://api.crustdata.com/company/enrich',observation_date=day.isoformat())]
    evidence.append(Evidence(company_id=name,category='funding_snapshot',fact='funding',value={'total_investment_usd':1000000,'last_fundraise_date':'2026-01-01','milestones':[{'funding_date':'2026-01-01','amount_usd':500000,'round_type':'series_a','investors':'A, B'}]},source='https://api.crustdata.com/company/enrich'))
    return Dossier(query=name,name=name,company_id=name,evidence=evidence)


def test_series_derived_stats_ordering_and_funding_provenance():
    d=dossier('A',[(100,10),(110,12),(130,15),(140,16),(150,18),(200,30),(240,34)])
    x=analyze(d)
    assert x['workforce']['latest']['value']==240
    assert x['workforce']['ewma']['value']==pytest.approx(185.26891734375)
    assert x['workforce']['six_month']['value']==pytest.approx(1.4)
    assert x['workforce']['ols_trend']['unit']=='count/day'
    assert x['workforce']['anomaly'] is not None
    assert x['funding']['value']==1_000_000 and x['metrics']['funding_total']['currency']=='USD'
    assert x['latest_round']['value']==500_000 and x['latest_round']['round_type']=='series_a'
    assert x['metrics']['latest_round']['investors']=='A, B'
    assert x['revenue'] is None and x['valuation'] is None and x['traffic'] is None
    assert x['funding']['evidence_ids']


def test_sparse_data_unknown_and_zero_mad_safe():
    x=analyze(dossier('Sparse',[(0,0),(0,0)]))
    assert x['workforce']['ewma'] is None and x['workforce']['ols_trend'] is None
    assert x['workforce']['six_month'] is None and x['workforce']['anomaly'] is None
    assert x['workforce']['volatility'] is None
    assert x['funding'] is not None
    y=analyze(Dossier(query='empty'))
    assert y['funding'] is None and y['workforce']['latest'] is None


def test_comparative_insights_are_operating_signals_not_winners():
    results,insights=compare([dossier('A',[(100,10),(120,12),(140,14),(160,16),(180,18),(200,20),(240,30)]),dossier('B',[(100,10),(110,11),(120,12),(130,13),(140,14),(150,15),(160,16)])])
    assert len(results)==2
    assert any('stronger observed workforce' in x for x in insights)
    assert any('historical funding does not indicate current cash' in x for x in insights)
    assert any('no winner is selected' in x for x in insights)


def test_invalid_future_and_duplicate_dates_excluded():
    d=dossier('A',[(100,10),(110,12),(130,15)])
    first=d.evidence[0]
    d.evidence += [first.model_copy(update={'id':'copy'}),first.model_copy(update={'id':'conflict','value':999}),first.model_copy(update={'id':'future','observation_date':'2099-01-01','value':9999}),first.model_copy(update={'id':'nan','value':float('nan')})]
    x=analyze(d)
    assert len(x['workforce']['points'])==2
    assert x['workforce']['latest']['value']==130
    assert x['workforce']['forecast'] is None


def test_hiring_intensity_same_dates_and_forecast_guard():
    x=analyze(dossier('A',[(100,10),(110,12),(130,15)]))
    assert x['hiring_intensity']['value']==pytest.approx(15/130)
    assert x['workforce']['forecast'] is None
    assert set(x['hiring_intensity']['evidence_ids'])<=set(x['evidence_ids'])


def test_projection_holdout_and_fit_rules():
    from autopsy.decision_insights import project,investor_fit
    from autopsy.mandate import Mandate
    from tests.test_vcos_finance import deal,dossier as financial_dossier
    end=date.today()
    pts=[{'date':(end-timedelta(days=30*(9-i))).isoformat(),'value':100+i*10} for i in range(10)]
    result=project({'points':pts})
    assert result['backtest_mae']==pytest.approx(0,abs=1e-9)
    assert result['projection']['value']==pytest.approx(200)
    assert project({'points':pts[:3]})['projection'] is None
    assert project({'points':pts},'EWMA',.2)['projection']['value']!=project({'points':pts},'EWMA',.8)['projection']['value']
    with pytest.raises(ValueError):project({'points':pts},horizon=365)
    d=deal(provenance='MODELED ASSUMPTIONS')
    assert investor_fit(Mandate(capital=100),d,financial_dossier(d))['status']=='Insufficient information to assess'
