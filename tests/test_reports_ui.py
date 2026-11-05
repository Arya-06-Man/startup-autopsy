import pytest
from autopsy.models import Run,Dossier,Evidence,Signal,Assessment
from autopsy.orchestrator import actions
from autopsy.reports import html,markdown,ledger
from streamlit.testing.v1 import AppTest


def test_reports_escape_and_ledger():
    d=Dossier(query='<script>alert(1)</script>'); d.advice=actions(d)
    run=Run(companies=[d],mode='SYNTHETIC TEST FIXTURES')
    assert '<script>' not in html(run)
    assert '&lt;script&gt;' in html(run)
    assert 'SYNTHETIC TEST FIXTURES' in markdown(run)
    assert Run.model_validate_json(ledger(run)).id==run.id


def test_report_rejects_fabricated_reference():
    d=Dossier(query='test',assessment=Assessment(signals=[Signal(category='hiring',severity=1,evidence_ids=['fake'],explanation='x')]))
    with pytest.raises(ValueError): markdown(Run(companies=[d]))


def test_empty_dashboard(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    from pathlib import Path
    app=Path(__file__).resolve().parents[1]/'app.py'
    at=AppTest.from_file(str(app)).run(timeout=20)
    assert not at.exception
    assert 'Startup Autopsy VCOS' in at.title[0].value
    assert 'Investment overview' in [s.value for s in at.subheader]


def test_populated_dashboard(tmp_path,monkeypatch):
    from pathlib import Path
    from datetime import date,timedelta
    from autopsy.storage import Store
    from autopsy.risk import assess
    dates=[(date.today()-timedelta(days=n)).isoformat() for n in (100,10)]
    evidence=[Evidence(company_id='1',category=c,fact='Synthetic count',value=v,source='https://example.test/source',event_date=dt)
              for c in ('workforce','hiring') for dt,v in zip(dates,(100,50))]
    d=Dossier(query='synthetic.test',name='Synthetic Company',company_id='1',domain='synthetic.test',evidence=evidence,status='complete',assessment=assess(evidence))
    d.advice=actions(d)
    Store(tmp_path/'data').save(Run(companies=[d],mode='SYNTHETIC TEST FIXTURES',status='complete'))
    monkeypatch.chdir(tmp_path)
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    at.radio[0].set_value('Evidence & Reports').run()
    assert not at.exception
    assert len(at.tabs)==6
    assert at.metric[1].value=='1'
    assert len(at.get('download_button'))==4
