"""Actions through the real Streamlit app; every provider is mocked, fixtures synthetic."""
import json
from datetime import date,timedelta
from pathlib import Path
import httpx
import pytest
from streamlit.testing.v1 import AppTest
from autopsy.api import Crustdata
from autopsy.llm import Planner
from autopsy.config import Settings
from autopsy.mandate import Workspace
from autopsy.committee import changes
from autopsy.vcos_reports import export


def field(at,kind,label): return next(w for w in getattr(at,kind) if w.label==label)
def click(at,label):
    field(at,'button',label).click().run(timeout=30)
    assert not at.exception, at.exception


def test_complete_investor_journey_a_through_f(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Settings,'load',classmethod(lambda cls:Settings(api_key='synthetic-test',gemini_key='synthetic-test',max_iterations=0)))
    api_calls=[]
    dates=[(date.today()-timedelta(days=n)).isoformat() for n in (100,10)]
    def company(cid):
        return {'crustdata_company_id':cid,'basic_info':{'name':f'SYNTHETIC Opportunity {cid}','primary_domain':f'synthetic-{cid}.test'},
            'headcount':{'timeseries':[{'date':d,'employee_count':v} for d,v in zip(dates,(100,110))]},
            'hiring':{'open_jobs_timeseries':[{'date':d,'open_jobs':v} for d,v in zip(dates,(10,11))]},
            'locations':{'country':'IND'}}
    def provider(req):
        body=json.loads(req.content); api_calls.append(req.url.path)
        if req.url.path=='/company/search': return httpx.Response(200,json={'companies':[company(1),company(2)],'next_cursor':None})
        cid=(body.get('crustdata_company_ids') or [1 if 'synthetic-1' in str(body) else 2])[0]
        return httpx.Response(200,json=[{'matches':[{'company_data':company(cid)}]}])
    def llm(req):
        if req.method=='GET': return httpx.Response(200,json={'models':[{'name':'models/gemini-3.5-flash','supportedGenerationMethods':['generateContent']}]})
        prompt=json.loads(req.content)['contents'][0]['parts'][0]['text']
        if 'VC research planner' in prompt: value={'focus':'stop','hypotheses':[],'questions':['Which primary records confirm the supplied inputs?']}
        else:
            data=json.loads(prompt.split('DATA: ',1)[1]); ref=next(iter(data['references']))
            value={'thesis':[{'claim':'The supplied assumptions require primary document verification.','references':[ref],'kind':'hypothesis'}],
                   'challenges':[],'questions':['What evidence would invalidate the thesis?']}
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(value)}]}}]})
    original_api=Crustdata.__init__; original_llm=Planner.__init__
    monkeypatch.setattr(Crustdata,'__init__',lambda self,settings,store,transport=None:original_api(self,settings,store,httpx.MockTransport(provider)))
    monkeypatch.setattr(Planner,'__init__',lambda self,settings,transport=None:original_llm(self,settings,httpx.MockTransport(llm)))
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    assert not at.exception
    # A: reviewed mandate, discovery, watchlist, explicit handoff, real investigation controls.
    field(at,'number_input','Total portfolio capital').set_value(100000000.)
    field(at,'text_input','Sector preferences (comma separated)').set_value('Software')
    field(at,'text_input','Geographic preferences (comma separated)').set_value('India')
    click(at,'Save reviewed mandate')
    assert at.session_state['mandate']['reserve_fraction']==.3
    at.radio[0].set_value('Discover').run()
    field(at,'text_input','Country label or ISO alpha-3').set_value('IND')
    click(at,'Search Crustdata')
    field(at,'multiselect','Shortlist 2–5 companies for deep diligence').set_value(['synthetic-1.test','synthetic-2.test']).run()
    field(at,'text_input','Watchlist name').set_value('Synthetic QA shortlist').run()
    click(at,'Save named watchlist')
    click(at,'Add selected to evaluation')
    assert at.radio[0].value=='Evaluate'
    click(at,'Investigate evaluation candidates')
    click(at,'Launch autonomous investigation')
    assert at.radio[0].value=='Evaluate' and len(at.session_state['evaluation_pool'])==2
    # B: both guided opportunity forms, supplied illustrative financials and terms.
    for cid in ('1','2'):
        field(at,'selectbox','Edit opportunity').set_value(cid).run()
        for label,value in [('Company sector','Software'),('Investment stage','seed'),('Company geography','India')]: field(at,'text_input',label).set_value(value)
        for label,value in [('Proposed cheque',20000000.),('Entry valuation',80000000.),('Total round size (0 = unknown)',20000000.),
                            ('Supplied cash balance',100000000.),('Supplied monthly net burn',1000000.),('Supplied annual revenue',50000000.),
                            ('Downside MOIC assumption',1.1),('Base MOIC assumption',2.),('Upside MOIC assumption',4.)]:
            field(at,'number_input',label).set_value(value)
        field(at,'checkbox','I am supplying dated company financials').set_value(True)
        field(at,'checkbox','Supply modeled outcome MOIC assumptions').set_value(True)
        field(at,'multiselect','Documents supplied · user attestation').set_value(['Financial statements','Cap table','Term sheet'])
        click(at,'Validate & save opportunity')
    assert len(at.session_state['vcos_deals'])==2
    # C: actual constrained allocation with reserve, then save the original decision.
    at.radio[0].set_value('Portfolio Lab').run()
    click(at,'Compute allocation & alternatives')
    assert sum(at.session_state['allocation']['allocations'].values())==pytest.approx(40000000.)
    assert at.session_state['allocation']['reserve']==30000000.
    at.radio[0].set_value('Investment Committee').run()
    click(at,'Challenge investment thesis')
    assert at.session_state['committee']['engine']=='GEMINI'
    click(at,'Save decision snapshot')
    # D: reactive scenario calculations and input persistence without pressing Run again.
    at.radio[0].set_value('War Room').run()
    for label,value in [('Available cash',100000000.),('Monthly net burn',1000000.),('Current ownership %',20.),
                        ('Total investor cost basis',20000000.),('Downside exit value',50000000.),('Base exit value',200000000.),('Upside exit value',500000000.)]:
        field(at,'number_input',label).set_value(value)
    click(at,'Run scenario comparison')
    assert at.session_state['war_outcomes']['Base']['moic']==pytest.approx(2)
    field(at,'number_input','Monthly net burn').set_value(2000000.).run()
    assert at.session_state['war_outcomes']['Base']['cash_exhaustion_month']==50
    at.radio[0].set_value('Overview').run()
    at.radio[0].set_value('War Room').run()
    assert field(at,'number_input','Monthly net burn').value==2000000.
    field(at,'number_input','Monthly net burn').set_value(1000000.).run()
    field(at,'selectbox','Opportunity for these modeled outcomes').set_value('1').run()
    field(at,'checkbox','I confirm these modeled assumptions apply to this opportunity').set_value(True).run()
    click(at,'Apply outcomes and invalidate prior allocation')
    assert at.session_state['vcos_deals'][0]['downside_moic']==pytest.approx(.5)
    at.radio[0].set_value('Portfolio Lab').run()
    click(at,'Compute allocation & alternatives')
    assert sum(at.session_state['allocation']['allocations'].values())==pytest.approx(20000000.)
    assert at.session_state['allocation']['allocations']['1']==0
    # E: refreshed committee, actual generated artifacts and resolvable citations.
    at.radio[0].set_value('Investment Committee').run()
    click(at,'Challenge investment thesis')
    assert len(at.get('download_button'))==3
    click(at,'Save decision snapshot')
    snapshots=Workspace(tmp_path/'data/vcos').list('snapshots')
    assert len(snapshots)==2 and changes(snapshots[1]['context'],snapshots[0]['context'])
    artifacts=export(snapshots[0]['context'],snapshots[0]['committee'])
    for extension,content in artifacts.items():
        (tmp_path/('synthetic-memo.'+extension)).write_text(content)
        assert content and 'SYNTHETIC Opportunity' in content
    assert json.loads(artifacts['json'])['context']['allocation']['allocations']['1']==0
    # F: reopening restores previous terms, allocation and original evidence, not the new decision.
    field(at,'selectbox','Prior snapshot').set_value(1).run()
    click(at,'Reopen prior scenario / decision')
    assert sum(at.session_state['allocation']['allocations'].values())==pytest.approx(40000000.)
    assert at.session_state['vcos_deals'][0]['downside_moic']==pytest.approx(1.1)
    assert len(at.session_state['replay_dossiers'])==2
    assert api_calls.count('/company/search')==1
    assert api_calls.count('/company/identify')==2 and api_calls.count('/company/enrich')==2
