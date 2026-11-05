import json
from pathlib import Path
import httpx
import pytest
from streamlit.testing.v1 import AppTest
from autopsy.api import Crustdata,ResearchError
from autopsy.config import Settings
from autopsy.storage import Store
from autopsy.mandate import Mandate,Workspace
from autopsy.discovery import search_companies,rows
from autopsy.llm import Planner
from autopsy.committee import context,review,changes
from autopsy.vcos_reports import export
from autopsy.models import Run
from tests.test_vcos_finance import deal,dossier


def test_discovery_contract_and_pagination(tmp_path):
    requests=[]
    def respond(req):
        body=json.loads(req.content); requests.append(body)
        assert req.url.path=='/company/search' and req.headers['x-api-version']=='2025-11-01'
        return httpx.Response(200,json={'companies':[{'crustdata_company_id':1,'basic_info':{'name':'Synthetic','primary_domain':'synthetic.test'}}],'next_cursor':'synth-next'})
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(respond))
    first=search_companies(api,country='IND',limit=2)
    search_companies(api,country='IND',limit=2,cursor=first['next_cursor'])
    assert requests[0]['filters']==requests[1]['filters']
    assert requests[1]['cursor']=='synth-next'
    assert rows(first)[0]['Headcount'] is None
    assert 'SINGLE-SOURCE' in rows(first)[0]['Source']
    with pytest.raises(ValueError): search_companies(api)
    with pytest.raises(ValueError): search_companies(api,country='IND',limit=100)


def test_discovery_rejects_wrong_shape_and_no_fake_fallback(tmp_path):
    api=Crustdata(Settings(api_key='test'),Store(tmp_path),httpx.MockTransport(lambda r:httpx.Response(200,json=[])))
    with pytest.raises(ResearchError): search_companies(api,country='IND')


def test_committee_fallback_reports_and_actual_diff():
    d=deal(); ctx=context(Mandate(capital=100),[d],{d.company_id:dossier(d)})
    planner=Planner(Settings())
    result=review(ctx,planner)
    assert result['engine']=='DETERMINISTIC FALLBACK' and len(result['perspectives'])==3
    artifacts=export(ctx,result)
    assert 'SYNTHETIC DEMO DATA' in artifacts['json']
    assert json.loads(artifacts['json'])['context']['deals'][0]['metrics']['ownership']==.2
    assert len(changes({'valuation':1},{'valuation':2}))==1
    assert changes({'valuation':1},{'valuation':2})[0]['before']==1
    assert changes(ctx,ctx)==[]
    assert changes({'deals':[{'terms':{'valuation':80}}]},{'deals':[{'terms':{'valuation':180}}]})[0]['path']=='deals[0].terms.valuation'
    malicious=context(Mandate(capital=100),[deal(name='<script>alert(1)</script>')],{})
    assert '<script>' not in export(malicious)['html']
    planner.close()


@pytest.mark.parametrize('bad_ref',[False,True])
def test_structured_role_passes_validate_refs(bad_ref):
    d=deal(); ctx=context(Mandate(capital=100),[d],{d.company_id:dossier(d)})
    def respond(req):
        text=json.dumps({'thesis':[{'claim':'Review supplied terms','references':['invented' if bad_ref else 'A-'+d.company_id]}],'challenges':[],'questions':[]})
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':text}]}}]})
    planner=Planner(Settings(gemini_key='test'),httpx.MockTransport(respond)); planner.model='models/synthetic-flash'
    result=review(ctx,planner)
    assert result['engine']==('DETERMINISTIC FALLBACK' if bad_ref else 'GEMINI')
    assert planner.calls==(1 if bad_ref else 3)  # Validation failure opens the circuit.
    planner.close()


def test_discovered_model_unavailable_bounded_fallback():
    calls=[]
    def respond(req):
        if req.method=='GET': return httpx.Response(200,json={'models':[{'name':name,'supportedGenerationMethods':['generateContent']} for name in ['models/gemini-1-flash','models/gemini-2-flash']]})
        calls.append(req.url.path)
        if 'gemini-2' in req.url.path: return httpx.Response(404)
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"focus":"stop"}'}]}}]})
    p=Planner(Settings(gemini_key='test'),httpx.MockTransport(respond))
    from autopsy.models import Dossier
    assert p.plan(Dossier(query='synthetic')) is not None
    assert p.calls==2 and p.model=='models/gemini-1-flash'
    p.close()


def app(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    m=Mandate(capital=100,min_cheque=5,max_cheque=25,company_limit=.25,sector_limit=.5,stage_limit=.75)
    Workspace(tmp_path/'data/vcos').save('mandates',m.model_dump(mode='json'))
    deals=[deal(),deal('synth-b')]
    Store(tmp_path/'data').save(Run(companies=[dossier(d) for d in deals],status='complete',mode='SYNTHETIC TEST FIXTURES'))
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
    at.session_state['vcos_deals']=[d.model_dump(mode='json') for d in deals]
    return at.run(timeout=30)


def button(at,label): return next(b for b in at.button if b.label==label)


def test_all_seven_workspace_routes(tmp_path,monkeypatch):
    at=app(tmp_path,monkeypatch)
    for section in ['Overview','Discover','Evaluate','Portfolio Lab','War Room','Investment Committee','Evidence & Reports']:
        at.radio[0].set_value(section).run(timeout=30)
        assert not at.exception, (section,at.exception)


def test_allocation_war_room_and_exports_workflow(tmp_path,monkeypatch):
    at=app(tmp_path,monkeypatch)
    at.radio[0].set_value('Portfolio Lab').run()
    button(at,'Compute allocation & alternatives').click().run()
    assert not at.exception
    assert sum(at.session_state['allocation']['allocations'].values())==pytest.approx(40)
    at.radio[0].set_value('War Room').run()
    next(n for n in at.number_input if n.label=='Available cash').set_value(100.)
    next(n for n in at.number_input if n.label=='Monthly net burn').set_value(10.)
    button(at,'Run scenario comparison').click().run()
    assert not at.exception
    assert at.session_state['war_outcomes']['Base']['cash_exhaustion_month']==10
    button(at,'Save scenario snapshot').click().run()
    assert len(Workspace(tmp_path/'data/vcos').list('snapshots'))==1
    at.radio[0].set_value('Investment Committee').run()
    assert not at.exception
    assert len(at.get('download_button'))==3
    button(at,'Save decision snapshot').click().run()
    assert len(Workspace(tmp_path/'data/vcos').list('snapshots'))==2


def test_mandate_validation_ui(tmp_path,monkeypatch):
    at=app(tmp_path,monkeypatch)
    at.radio[0].set_value('Investment Mandate').run()
    editor=next(t for t in at.text_area if t.key=='mandate_json')
    value=json.loads(editor.value); value['company_limit']=2
    editor.set_value(json.dumps(value))
    button(at,'Validate & save mandate').click().run()
    assert at.error and not at.exception
    value['company_limit']=.2
    next(t for t in at.text_area if t.key=='mandate_json').set_value(json.dumps(value))
    button(at,'Validate & save mandate').click().run()
    assert not at.exception and at.success


def test_bad_json_and_replay_preserve_actual_scenario(tmp_path,monkeypatch):
    at=app(tmp_path,monkeypatch)
    at.radio[0].set_value('Investment Mandate').run()
    next(t for t in at.text_area if t.key=='mandate_json').set_value('{invalid json')
    button(at,'Validate & save mandate').click().run()
    assert at.error and not at.exception
    at.radio[0].set_value('War Room').run()
    next(n for n in at.number_input if n.key=='war_cash').set_value(123.)
    next(n for n in at.number_input if n.key=='war_burn').set_value(10.)
    button(at,'Run scenario comparison').click().run()
    button(at,'Save scenario snapshot').click().run()
    next(n for n in at.number_input if n.key=='war_cash').set_value(456.)
    button(at,'Run scenario comparison').click().run()
    button(at,'Reopen prior scenario / decision').click().run()
    assert not at.exception
    assert next(n for n in at.number_input if n.key=='war_cash').value==123.
    assert at.session_state['war_outcomes']['Base']['assumptions']['cash']==123.


def test_memo_rejects_invalid_committee_refs():
    d=deal(); ctx=context(Mandate(capital=100),[d],{d.company_id:dossier(d)})
    with pytest.raises(ValueError):
        export(ctx,{'perspectives':[{'thesis':[{'claim':'Unsupported','references':['fake']}]}]})


def test_replay_restores_decision_and_frozen_evidence(tmp_path,monkeypatch):
    at=app(tmp_path,monkeypatch)
    at.radio[0].set_value('Investment Committee').run()
    button(at,'Save decision snapshot').click().run()
    button(at,'Reopen prior scenario / decision').click().run()
    assert not at.exception
    assert len(at.session_state['replay_dossiers'])==2
    assert len(at.session_state['vcos_deals'])==2
