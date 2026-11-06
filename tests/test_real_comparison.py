"""Local acceptance against private saved evidence; not committed as a fixture."""
from pathlib import Path
from io import BytesIO
import pytest
from streamlit.testing.v1 import AppTest
from autopsy.storage import Store
from autopsy.models import Run
from autopsy.mandate import Workspace,Mandate
from autopsy.finance import Deal,deal_metrics
from autopsy.company_intelligence import analyze


def test_saved_retool_whatsapp_selection_with_unrelated_context(tmp_path,monkeypatch):
    root=Path(__file__).resolve().parents[1]
    ids=['633593','631281']
    pair=next((r for r in Store(root/'data').runs() if all(any(d.company_id==cid and d.status=='complete' for d in r.companies) for cid in ids)),None)
    if pair is None: pytest.skip('Private real investigation is available only in the local workspace')
    # Copy into an isolated directory; preserve private histories and avoid all provider calls.
    monkeypatch.chdir(tmp_path)
    store=Store();store.save(pair)
    unrelated=Run(companies=[],status='complete');store.save(unrelated)
    mandate=Mandate(capital=100000000,max_cheque=25000000)
    Workspace().save('mandates',mandate.model_dump(mode='json'))
    ds={d.company_id:d for d in pair.companies}
    for cid,expected in zip(ids,[-.0193,.0785]):
        assert analyze(ds[cid])['workforce']['three_month']['value']==pytest.approx(expected,abs=.001)
    at=AppTest.from_file(str(root/'app.py'))
    at.session_state['vcos_section']='Evaluate'
    at.session_state['evidence_run_id']=unrelated.id
    at.session_state['evaluation_pool']={cid:{'name':ds[cid].name,'domain':ds[cid].domain} for cid in ids}|{'uninvestigated-third':{'name':'Third company','domain':'third.test'}}
    deals=[Deal(company_id=cid,name=ds[cid].name,investment=20000000,valuation=220000000,round_size=20000000,provenance='MODELED ASSUMPTIONS') for cid in ids]
    at.session_state['vcos_deals']=[d.model_dump(mode='json') for d in deals]
    at.run(timeout=30)
    assert not at.exception
    select=next(w for w in at.multiselect if w.label=='Companies from evidence context')
    select.set_value(ids).run(timeout=30)
    assert not at.exception
    tables=[df.value for df in at.dataframe]
    table=next(t for t in tables if 'Indicator' in t.columns and 'Retool' in t.columns and 'WhatsApp' in t.columns)
    row=table[table['Indicator']=='Workforce · 3-month'].iloc[0]
    assert row['Retool']=='-1.9%' and row['WhatsApp']=='7.8%'
    assert not any('No investigated evidence linked' in t.value for t in at.caption)
    assert deal_metrics(deals[0])['ownership']==pytest.approx(1/12)
    assert any('8.33%' in m.value for m in at.metric)
    at.radio[0].set_value('Investment Committee').run(timeout=30)
    assert not at.exception
    next(b for b in at.button if b.label=='Generate Report').click().run(timeout=30)
    next(b for b in at.button if b.label=='Generate PDF').click().run(timeout=30)
    assert not at.exception
    pdf=at.session_state['generated_pdf_'+at.session_state['report_selection']]
    from pypdf import PdfReader
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert 'Retool' in text and 'WhatsApp' in text and '8.33%' in text
    assert 'Company intelligence and operating momentum' in text
    assert 'Insufficient history' in text
