"""Presentation workflows with synthetic identities and no external API calls."""
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest
from autopsy.config import Settings
from autopsy.identity import IdentityError
from autopsy.api import ResearchError
from autopsy.mandate import Workspace,Mandate
from tests.test_vcos_workflows import app,button


def fresh(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Settings,'load',classmethod(lambda cls:Settings(api_key='synthetic-key')))
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)


def test_home_navigation_onboarding_and_guided_prerequisites(tmp_path,monkeypatch):
    at=fresh(tmp_path,monkeypatch)
    assert at.title[0].value=='Investment Intelligence'
    assert any(t.label=='Search companies' for t in at.text_input)
    button(at,'Open VC War Room').click().run()
    assert at.radio[0].value=='War Room' and not at.exception
    at.radio[0].set_value('Investment Committee').run()
    assert button(at,'Create Investment Mandate')
    button(at,'Create Investment Mandate').click().run()
    assert at.radio[0].value=='Investment Mandate'
    button(at,'Save reviewed mandate').click().run()
    assert Workspace().mandates()
    at.radio[0].set_value('Investment Committee').run()
    assert button(at,'Go to Deal Comparison')
    at.radio[0].set_value('Overview').run()
    button(at,'Skip guide').click().run()
    assert Workspace().list('preferences')[0]['onboarding_skipped']
    assert not any(b.label=='Skip guide' for b in at.button)
    for route in ['Company Search','Reports','Investigation History','Company Overview']:
        at.radio[0].set_value(route).run()
        assert not at.exception


def test_submitted_search_actions_persist_without_repeated_lookup(tmp_path,monkeypatch):
    from autopsy import interface
    calls=[]
    def lookup(api,query,**kwargs):
        calls.append(query)
        return {'crustdata_company_id':123,'basic_info':{'name':'SYNTHETIC Company','primary_domain':'synthetic.test'}},{'mode':'SYNTHETIC DEMO DATA','retrieved_at':'2026-01-01T00:00:00Z'},'Exact synthetic identity'
    monkeypatch.setattr(interface,'identify_company',lookup)
    at=fresh(tmp_path,monkeypatch)
    next(t for t in at.text_input if t.label=='Search companies').set_value('synthetic.test')
    button(at,'Search').click().run()
    assert len(calls)==1 and not at.exception
    at.run(); assert len(calls)==1
    button(at,'Add to Watchlist').click().run()
    assert Workspace().list('watchlists')[0]['domains']==['synthetic.test']
    button(at,'View Company').click().run()
    assert at.radio[0].value=='Company Overview'
    button(at,'Investigate').click().run()
    assert at.radio[0].value=='Evidence & Reports'
    assert any(t.value=='synthetic.test' for t in at.text_area)
    at.radio[0].set_value('Company Search').run()
    button(at,'Add to Compare').click().run()
    assert at.radio[0].value=='Evaluate'
    assert '123' in Workspace().list('comparisons')[0]['pool']
    assert len(calls)==1


def test_search_errors_and_manual_disambiguation(tmp_path,monkeypatch):
    from autopsy import interface
    calls=[]
    candidate={'company_id':'123','name':'SYNTHETIC Choice','domain':'synthetic.test','retrieved_at':'2026-01-01','confidence':.6,'mode':'SYNTHETIC DEMO DATA'}
    def lookup(api,query,selection=None,**kwargs):
        calls.append(selection)
        if not selection: raise IdentityError('Ambiguous',[candidate])
        return {'crustdata_company_id':123,'basic_info':{'name':candidate['name'],'primary_domain':candidate['domain']}},{'mode':candidate['mode'],'retrieved_at':candidate['retrieved_at']},'Manual'
    monkeypatch.setattr(interface,'identify_company',lookup)
    at=fresh(tmp_path,monkeypatch)
    button(at,'Search').click().run()
    assert 'Enter a company' in at.warning[0].value and not calls
    next(t for t in at.text_input if t.label=='Search companies').set_value('Synthetic')
    button(at,'Search').click().run()
    assert not Workspace().list('companies') and button(at,'Confirm company').disabled
    next(c for c in at.checkbox if c.label=='I confirm this company name and domain').check().run()
    button(at,'Confirm company').click().run()
    assert calls[-1]==candidate and Workspace().list('companies')
    monkeypatch.setattr(interface,'identify_company',lambda *a,**k:(_ for _ in ()).throw(ResearchError('Provider request failed: HTTP 429')))
    button(at,'Search').click().run()
    assert any('429' in w.value for w in at.warning) and not at.exception
    assert not any(b.label=='View Company' for b in at.button)


def test_committee_report_library_all_exports(tmp_path,monkeypatch):
    at=app(tmp_path,monkeypatch)
    at.radio[0].set_value('Investment Committee').run()
    button(at,'Generate Report').click().run(timeout=30)
    assert not at.exception
    assert at.radio[0].value=='Reports'
    assert {b.label for b in at.get('download_button')}=={'Download PDF','Print Report','Download HTML','Download Markdown','Export JSON'}
    saved=Workspace().list('reports')
    assert len(saved)==1 and len(saved[0]['context']['deals'])==2
    assert any('Report saved '+saved[0]['created_at'] in m.value for m in at.markdown)
    assert not any('Retrieved '+saved[0]['created_at'] in m.value for m in at.markdown)
    button(at,'Open Report').click().run()
    assert not at.exception
    at.radio[0].set_value('Overview').run()
    assert any('Recent reports' in m.value for m in at.markdown)


def test_single_company_investigation_opens_dossier(tmp_path,monkeypatch):
    from autopsy import interface,orchestrator
    from autopsy.models import Run
    from tests.test_vcos_finance import deal,dossier
    def lookup(*args,**kwargs):
        return {'crustdata_company_id':123,'basic_info':{'name':'SYNTHETIC Company','primary_domain':'synthetic.test'}},{'mode':'SYNTHETIC DEMO DATA','retrieved_at':'2026-01-01'},'Synthetic identity'
    def investigate(queries,api,store,*args,**kwargs):
        d=dossier(deal('123'));d.name='SYNTHETIC Company';d.domain='synthetic.test'
        run=Run(companies=[d],status='complete',mode='SYNTHETIC DEMO DATA');store.save(run);return run
    monkeypatch.setattr(interface,'identify_company',lookup)
    monkeypatch.setattr(orchestrator,'investigate',investigate)
    at=fresh(tmp_path,monkeypatch)
    next(t for t in at.text_input if t.label=='Search companies').set_value('synthetic.test')
    button(at,'Search').click().run();button(at,'Investigate').click().run()
    button(at,'Launch autonomous investigation').click().run()
    assert not at.exception and at.radio[0].value=='Company Overview'
    assert at.title[0].value=='SYNTHETIC Company'
