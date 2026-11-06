"""Persistent local document library with actual print-ready PDF artifacts."""
import json
import pandas as pd
import streamlit as st
from autopsy import reports
from autopsy import interface as ui
from autopsy.vcos_reports import export,validate
from autopsy.pdf_reports import committee_pdf,investigation_pdf


@st.cache_data(show_spinner=False,max_entries=24)
def committee_artifacts(serialized):
    record=json.loads(serialized)
    artifacts=export(record['context'],record.get('committee'))
    artifacts['pdf']=committee_pdf(record['context'],record.get('committee'))
    return artifacts


@st.cache_data(show_spinner=False,max_entries=24)
def research_artifacts(serialized):
    from autopsy.models import Run
    run=Run.model_validate_json(serialized)
    return {'html':reports.html(run),'md':reports.markdown(run),'json':reports.ledger(run),'pdf':investigation_pdf(run)}


def save_committee_report(workspace,context,committee):
    validate(context,committee)
    modes=sorted({v.get('data_mode','Unknown') for k,v in context['references'].items() if not k.startswith('A-')})
    return workspace.save('reports',{'title':'Investment Committee - '+', '.join(d['terms']['name'] for d in context['deals']),
        'report_type':'Investment Committee','companies':[d['terms']['name'] for d in context['deals']],
        'status':'Committee generated' if committee else 'Draft - committee not generated',
        'source_mode':' + '.join(modes) or 'No external evidence','context':context,'committee':committee})


def report_controls(artifacts,stem,key,include_pdf=True):
    if include_pdf:
        a,b=st.columns([2,1])
        a.download_button('Download PDF',artifacts['pdf'],stem+'.pdf','application/pdf',type='primary',key=key+'_pdf',width='stretch')
        b.download_button('Print Report',artifacts['pdf'],stem+'-print.pdf','application/pdf',key=key+'_print',width='stretch')
        st.caption('Print Report downloads the same A4 PDF. Open it and use your PDF viewer’s Print command.')
    a,b,c=st.columns(3)
    a.download_button('Download HTML',artifacts['html'],stem+'.html','text/html',key=key+'_html',width='stretch')
    b.download_button('Download Markdown',artifacts['md'],stem+'.md','text/markdown',key=key+'_md',width='stretch')
    c.download_button('Export JSON',artifacts['json'],stem+'.json','application/json',key=key+'_json',width='stretch')
    if st.button('Open Report',key=key+'_open',width='stretch'): st.session_state['preview_report']=key
    if st.session_state.get('preview_report')==key:
        import streamlit.components.v1 as components
        components.html(artifacts['html'],height=820,scrolling=True)


def reports_page(store,workspace):
    ui.heading('Reports',ui.DESCRIPTIONS['Reports'],'DOCUMENTS')
    options=[]
    for record in workspace.list('reports'):
        options.append({'id':'report_'+record['id'],'title':record['title'],'type':record['report_type'],
            'companies':', '.join(record['companies']),'date':record['created_at'],'status':record['status'],'mode':record['source_mode'],'record':record})
    for record in workspace.list('snapshots'):
        if record.get('kind')!='decision' or not record.get('context'): continue
        options.append({'id':'snapshot_'+record['id'],'title':'Decision snapshot','type':'Investment Committee',
            'companies':', '.join(d['terms']['name'] for d in record['context']['deals']),'date':record['created_at'],
            'status':'Saved decision','mode':'Preserved snapshot provenance','record':record})
    for run in store.runs():
        options.append({'id':'run_'+run.id,'title':'Company research briefing','type':'Research Briefing',
            'companies':', '.join(d.name or d.query for d in run.companies),'date':run.created_at,'status':run.status,
            'mode':run.mode,'run':run})
    options.sort(key=lambda r:r['date'],reverse=True)
    if not options:
        ui.empty('Your report library starts here.','Investigate companies for a research briefing, or compare opportunities for a committee memo.','Search Companies','Company Search')
        if st.button('Go to Investment Committee'): ui.go('Investment Committee')
        return
    st.dataframe(pd.DataFrame([{'Type':r['type'],'Companies covered':r['companies'],'Record created':r['date'][:19],
        'Status':r['status'],'Source mode':r['mode']} for r in options]),hide_index=True,width='stretch')
    ids=[r['id'] for r in options]
    requested=st.session_state.pop('requested_report_id',None)
    if requested in ids: st.session_state['report_selection']=requested
    if st.session_state.get('report_selection') not in ids: st.session_state.pop('report_selection',None)
    selected=st.selectbox('Open a report',ids,key='report_selection',format_func=lambda value:next(r['type']+' · '+r['companies']+' · '+r['date'][:16] for r in options if r['id']==value))
    item=next(r for r in options if r['id']==selected)
    with st.container(border=True):
        st.subheader(item['title'])
        st.markdown('**Companies:** '+item['companies'])
        ui.source_tags(item['mode'],item['date'],timestamp_label='Investigation started' if 'run' in item else 'Report saved')
        st.caption('Selected report · '+item['date']+' · PDF creation time appears inside the downloaded document.')
        st.caption(item['type']+' · '+item['status'])
        try:
            serialized=item['run'].model_dump_json() if 'run' in item else json.dumps({'context':item['record']['context'],'committee':item['record'].get('committee')},sort_keys=True)
            artifacts=research_artifacts(serialized) if 'run' in item else committee_artifacts(serialized)
            pdf_key='generated_pdf_'+item['id']
            if st.button('Generate PDF',type='primary',key='generate_'+item['id'],width='stretch'):
                with st.spinner('Validating selected decision and creating print-ready PDF'):
                    st.session_state[pdf_key]=artifacts['pdf']
                st.success('PDF generated from this selected saved report.')
            current_pdf=st.session_state.get(pdf_key)
            if current_pdf:
                a,b=st.columns([2,1])
                a.download_button('Download PDF',current_pdf,'vcos-'+item['id']+'.pdf','application/pdf',type='primary',key='download_'+item['id'],width='stretch')
                b.download_button('Print Report',current_pdf,'vcos-'+item['id']+'-print.pdf','application/pdf',key='print_'+item['id'],width='stretch')
                st.caption('Print Report downloads the same A4 PDF. Open it and use your PDF viewer’s Print command.')
            report_controls(artifacts,'vcos-'+item['id'],item['id'],include_pdf=False)
        except (ValueError,TypeError,KeyError) as exc: st.error('Report validation failed. Downloads are withheld: '+str(exc))
    if st.button('Create investment committee report'): ui.go('Investment Committee')
