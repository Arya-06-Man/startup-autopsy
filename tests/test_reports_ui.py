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
    assert 'Your portfolio.' in at.title[0].value
