"""Native PDF regression checks; fixtures are synthetic and never use network."""
from io import BytesIO
import pymupdf as fitz
import pytest
from pypdf import PdfReader
from autopsy.committee import context
from autopsy.finance import Scenario,simulate
from autopsy.mandate import Mandate
from autopsy.models import Run,Evidence
from autopsy.pdf_reports import committee_pdf,investigation_pdf,Report
from tests.test_vcos_finance import deal,dossier


def test_pdf_uses_validated_metrics_sources_and_a4():
    d=deal(); ctx=context(Mandate(capital=100),[d],{d.company_id:dossier(d)})
    ctx['war_room']={'Base':simulate(Scenario(cash=100,monthly_burn=1,years=5,ownership=.2,invested=20,exit_value=1000))}
    pdf=committee_pdf(ctx); reader=PdfReader(BytesIO(pdf))
    text='\n'.join(p.extract_text() for p in reader.pages)
    assert len(reader.pages)>=4
    for expected in ['Investment Committee Report','20.00%','100.00','SYNTHETIC DEMO DATA','War Room scenarios','PDF generated','Page 1']:
        assert expected in text
    assert all(abs(float(p.mediabox.width)-595.28)<.1 for p in reader.pages)
    assert any(a.get_object().get('/A',{}).get('/URI')=='https://example.test' for p in reader.pages for a in p.get('/Annots',[]))
    ctx['deals'][0]['metrics']['ownership']=.9
    with pytest.raises(ValueError,match='Stale financial'): committee_pdf(ctx)


def test_multipage_table_long_names_and_missing_data(tmp_path):
    report=Report('Synthetic Layout Regression','2026-01-01','No live company data')
    report.cover(['Synthetic '+('Very Long Company Name ' * 18)],'SYNTHETIC DEMO DATA')
    report.section('Multipage table')
    report.table(['Company','Diligence record'],[['Synthetic '+str(i),'Long evidence description ' * 20] for i in range(65)],[1,3])
    pdf=report.build(); path=tmp_path/'layout.pdf'; path.write_bytes(pdf)
    doc=fitz.open(stream=pdf,filetype='pdf')
    assert len(doc)>5
    for page in doc:
        text=page.get_text()
        assert f'Page {page.number+1}' in text
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    x0,y0,x1,y1=span['bbox']
                    assert x0>=45 and x1<=page.rect.width-45
                    assert y0>=20 and y1<=page.rect.height-18
    d=deal(cash=None,monthly_burn=None,revenue=None); ctx=context(Mandate(capital=100),[d],{})
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(committee_pdf(ctx))).pages)
    assert 'Unknown' in text and 'No allocation computed' in text


def test_research_pdf_preserves_dates_conflicts_and_escapes_markup():
    d=dossier(deal(name='<script> Synthetic & Company'))
    d.evidence[0].observation_date='2026-01-01'; d.evidence[0].data_mode='SYNTHETIC DEMO DATA'
    d.evidence.append(Evidence(company_id=d.company_id,category='news_observation',fact='Conflicting source <b>untrusted</b>',value='unknown',source='javascript:alert(1)',status='disputed/conflicting'))
    pdf=investigation_pdf(Run(companies=[d],status='complete',mode='SYNTHETIC DEMO DATA'))
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert '<script>' in text and '2026-01-01' in text and 'disputed/conflicting' in text
    assert 'source link unavailable' in text
