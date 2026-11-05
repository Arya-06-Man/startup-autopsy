"""Launch: streamlit run app.py"""
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from autopsy.config import Settings
from autopsy.storage import Store
from autopsy.api import Crustdata
from autopsy.llm import Planner
from autopsy.ingestion import ingest
from autopsy.orchestrator import investigate
from autopsy import reports
from autopsy.risk import runway
from autopsy.evidence import safe_url
from autopsy.vcos_ui import render
from autopsy.risk import metric_date

st.set_page_config(page_title='Startup Autopsy VCOS',page_icon='◈',layout='wide')
st.markdown('''<style>
.block-container{padding-top:2.5rem;max-width:1500px}h1{font-weight:650!important;letter-spacing:-.045em}h2{letter-spacing:-.025em}div[data-testid="stMetric"]{background:#121c2a;border:1px solid #263448;border-radius:12px;padding:20px}div[data-testid="stMetricLabel"]{color:#93a5bd}.eyebrow{font-size:.75rem;letter-spacing:.2em;color:#58dac2;font-weight:650}.intro{color:#93a5bd;max-width:780px;font-size:1.05rem}.stTabs [data-baseweb="tab-list"]{gap:24px}a{color:#58dac2}section[data-testid="stSidebar"]{border-right:1px solid #263448}div[data-testid="stExpander"]{border-color:#263448}
</style>''',unsafe_allow_html=True)
settings=Settings.load(); store=Store()
with st.sidebar:
    st.markdown('### ◈ STARTUP AUTOPSY')
    st.caption('VENTURE CAPITAL OPERATING SYSTEM')
    st.divider()
    st.markdown('**Detect → Investigate → Verify**  \nAssess → Recommend → Report')
    st.caption('Autonomous analyst service for investor follow-up.')
    st.divider()
    st.markdown('**Connection status**')
    st.write('● Crustdata key configured' if settings.api_key else '○ Crustdata key required')
    st.write('● Gemini configured' if settings.gemini_key else '● Deterministic research enabled')
    st.caption('A configured key is validated on its first request.')
    with st.expander('Investigation limits'):
        settings.max_calls=st.number_input('Maximum API attempts',min_value=1,max_value=100,value=max(1,min(100,settings.max_calls)))
        settings.max_credits=st.number_input('Estimated credit ceiling',min_value=1.0,max_value=500.0,value=max(1.,min(500.,settings.max_credits)))
        settings.max_iterations=st.slider('Follow-up iterations / company',0,4,min(4,max(0,settings.max_iterations)))
        st.caption('Enrichment reserves 5 estimated credits per call. Actual plan prices may vary; this is an estimate ceiling, not a guaranteed billing cap. Retries consume the attempt budget.')
    st.caption('ContextCon 04 · IIT Kanpur  \nInvesting / Services, Replaced')

st.markdown('<div class="eyebrow">AUTONOMOUS VENTURE CAPITAL INTELLIGENCE & DECISION PLATFORM</div>',unsafe_allow_html=True)
st.title('Startup Autopsy VCOS')
section=render(settings,store)
if section not in ('Discover','Evidence & Reports'): st.stop()
if section=='Discover':
    if st.session_state.get('shortlist_text'):
        st.session_state['investigation_queries']=st.session_state.pop('shortlist_text')
with st.expander('Launch investigation',expanded=not bool(store.runs())):
    left,right=st.columns([3,2])
    with left:
        text=st.text_area('Company names or domains',placeholder='retool.com\nnotion.so\nlinear.app',height=130,key='investigation_queries',help='One company per line. Up to five unique companies. Domains resolve more precisely.')
    with right:
        upload=st.file_uploader('Or upload portfolio CSV',type=['csv'])
        st.caption('Column: company, name, or domain. CSV and pasted entries are combined and deduplicated.')
        st.download_button('Download sample CSV','domain\nretool.com\nnotion.so\nlinear.app\n','sample_portfolio.csv','text/csv')
    launch=st.button('Launch autonomous investigation',type='primary',disabled=not settings.api_key)
    settings.refresh_data=st.checkbox('Refresh provider data for this investigation',help='Bypass the response cache on launch. This retrieves provider data again; it does not guarantee a new underlying observation. Prior investigations remain unchanged.')
    if not settings.api_key: st.info('Add CRUSTDATA_API_KEY to .env to enable live investigations. Previous real runs remain available below.')
    if launch:
        try:
            queries=ingest(text,upload.getvalue() if upload else None)
            with st.status('Investigation in progress',expanded=True) as status:
                progress=st.progress(0)
                stages=['PLAN','GATHER','DETECT','HYPOTHESIZE','INVESTIGATE','VERIFY','ASSESS','DELIVER']
                def update(company,stage,detail):
                    progress.progress(min(1.,(queries.index(company)+ (stages.index(stage)+1)/8)/len(queries)))
                    st.write(f'**{company} · {stage}** — {detail}')
                api=Crustdata(settings,store); planner=Planner(settings)
                try: run=investigate(queries,api,store,planner,update,identity_selections=st.session_state.get('identity_selections'))
                finally: api.close(); planner.close()
                st.session_state['run_id']=run.id
                st.session_state['requested_run_id']=run.id
                status.update(label='Investigation saved · '+run.status,state='complete' if run.status=='complete' else 'error',expanded=False)
            if run.status=='complete':
                st.session_state['requested_section']='Evaluate'; st.rerun()
        except ValueError as exc: st.error(str(exc))

if section=='Discover': st.stop()
runs=store.runs()
if not runs:
    st.divider()
    st.markdown('### An analyst workflow, from intake to delivery')
    cols=st.columns(3)
    for c,title,desc in zip(cols,['01 / Resolve & gather','02 / Investigate & verify','03 / Assess & act'],['Canonical company identity, workforce histories, hiring and business records.','Evidence-dependent follow-up research, fetched sources and a transparent decision trail.','Explainable priority, founder questions, draft follow-up and exportable evidence.']):
        c.markdown('**'+title+'**'); c.write(desc)
    st.info('No investigations yet. Start with company domains above. No synthetic data is substituted into live results.')
    st.stop()

ids=[r.id for r in runs]
selected=st.session_state.get('evidence_run_id',ids[0])
run=next(r for r in runs if r.id==selected)
if run.status=='running': st.warning('Interrupted investigation: completed stages are preserved. Launch a new run to continue research using cached responses.')
st.caption(f'{run.mode}  ·  Investigation {run.id}  ·  {run.created_at}  ·  Execution: {run.status.upper()} · Engine: {run.usage.get("analysis_engine", "Legacy: inspect trace")}')
companies=[d for d in run.companies if d.status!='duplicate']
metrics=st.columns(4)
metrics[0].metric('Companies resolved',sum(bool(d.company_id) for d in companies))
metrics[1].metric('Urgent reviews',sum(d.assessment.label=='Urgent review' for d in companies))
metrics[2].metric('Inconclusive assessments',sum(d.assessment.score is None for d in companies))
metrics[3].metric('Evidence observations',sum(len(d.evidence) for d in companies))
command,radar,dossier_tab,timeline,actions_tab,exports=st.tabs(['Command center','Risk radar','Company dossiers','Evidence timeline','Investor actions','Reporting center'])

with command:
    st.subheader('Portfolio command center')
    a,b=st.columns([3,2])
    with a:
        st.markdown('**Major observed trends**')
        findings=0
        for d in companies:
            for s in d.assessment.signals:
                findings+=1
                st.write(f'**{d.name} · {s.category}** — {s.explanation}')
                st.caption('Single-provider trend · '+', '.join(s.evidence_ids))
        if not findings: st.info('No sufficiently dated comparable trends. Review missing evidence and source leads in the dossiers.')
        st.caption('Independently corroborated findings: '+str(sum(e.status=='corroborated observation' for d in companies for e in d.evidence)))
    with b:
        counts=pd.Series([d.assessment.label for d in companies]).value_counts().rename_axis('Priority').reset_index(name='Companies')
        fig=px.pie(counts,names='Priority',values='Companies',hole=.7,color_discrete_sequence=['#58dac2','#e7b868','#ed7285','#7299d6'])
        fig.update_layout(height=280,margin=dict(t=10,b=10,l=0,r=0),paper_bgcolor='rgba(0,0,0,0)',legend=dict(orientation='h'))
        st.plotly_chart(fig,width='stretch')
    st.caption(reports.DISCLAIMER)

with radar:
    st.subheader('Investigation priority radar')
    ranked=sorted(companies,key=lambda d:d.assessment.score if d.assessment.score is not None else -1,reverse=True)
    frame=pd.DataFrame([{'Company':d.name or d.query,'Priority':d.assessment.score,'Assessment':d.assessment.label,'Coverage %':d.assessment.coverage,'Response':d.advice.get('urgency','Review identity'),'Status':d.status} for d in ranked])
    st.dataframe(frame,hide_index=True,width='stretch',column_config={'Priority':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.1f'),'Coverage %':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.0f%%')})
    st.caption('Blank priority means insufficient evidence. Weights: workforce 35%, leadership 30%, hiring 20%, business 15%. Only supported categories contribute; at least 50% weighted coverage and two comparable categories are required. This MVP scores dated workforce and hiring trends; leadership and business sources require manual verification before scoring.')
    scored=frame.dropna(subset=['Priority'])
    if not scored.empty:
        st.plotly_chart(px.bar(scored,x='Priority',y='Company',orientation='h',range_x=[0,100],color_discrete_sequence=['#58dac2']),width='stretch')

with dossier_tab:
    choice=st.selectbox('Open company dossier',range(len(companies)),format_func=lambda i:companies[i].name or companies[i].query)
    d=companies[choice]
    st.subheader(d.name or d.query)
    st.caption(f'{d.domain} · Crustdata ID {d.company_id or "unresolved"} · {d.assessment.label}')
    if d.metadata.get('description'): st.write(d.metadata['description'])
    for error in d.errors: st.warning(error)
    workforce=[{'Date':metric_date(e),'Employees':e.value} for e in d.evidence if e.category=='workforce' and e.status!='disputed/conflicting']
    hiring=[{'Date':metric_date(e),'Open roles':e.value} for e in d.evidence if e.category=='hiring' and e.status!='disputed/conflicting']
    a,b=st.columns(2)
    for col,rows,field in [(a,workforce,'Employees'),(b,hiring,'Open roles')]:
        with col:
            if len(rows)>1:
                df=pd.DataFrame(rows).sort_values('Date'); st.plotly_chart(px.line(df,x='Date',y=field,color_discrete_sequence=['#58dac2']),width='stretch')
            else: st.info(field+': dated history unavailable.')
    for s in d.assessment.signals:
        st.markdown('**'+s.category.title()+'**'); st.write(s.explanation); st.caption('Evidence: '+', '.join(s.evidence_ids)+' · Alternative explanations: '+'; '.join(s.alternatives))
    st.markdown('**Unresolved evidence requirements**')
    for missing in d.assessment.missing: st.write('• '+missing)
    with st.expander('Leadership, funding and business observations'):
        other=[e for e in d.evidence if e.category in ('leadership_snapshot','funding','business_raw')]
        if not other: st.info('No structured leadership, funding or news observations available.')
        for e in other:
            st.write(e.fact); st.caption(f'{e.id} · {e.event_date or "Effective date unknown"} · {e.status}'); st.json(e.value,expanded=False)
    with st.expander('Autonomous decision trail'):
        for t in d.trace: st.write('**'+t['stage']+'** · '+t['detail']); st.caption(t['at'])
    with st.expander('Company metadata'): st.json(d.metadata)

with timeline:
    st.subheader('Evidence timeline & source ledger')
    name=st.selectbox('Company filter',['All companies']+[d.name or d.query for d in companies])
    categories=sorted({e.category for d in companies for e in d.evidence})
    chosen=st.multiselect('Categories',categories,default=categories)
    for d in companies:
        if name!='All companies' and name!=(d.name or d.query): continue
        items=sorted([e for e in d.evidence if e.category in chosen],key=lambda e:e.event_date or e.publication_date or e.retrieved_at,reverse=True)
        st.markdown('### '+(d.name or d.query))
        total_pages=max(1,(len(items)+24)//25)
        page=st.number_input(f'Evidence page · {d.name or d.query} ({len(items)} observations)',min_value=1,max_value=total_pages,value=1,key='page_'+run.id+d.query)
        for e in items[(page-1)*25:page*25]:
            with st.expander(f'{e.event_date or e.publication_date or "Undated"} · {e.category} · {e.fact[:100]} · {e.id}'):
                st.write(e.fact); st.caption(f'{e.status} · {e.provider} · Observation: {e.observation_date or "unknown"} · Event: {e.event_date or "unknown"} · Publication: {e.publication_date or "unknown"} · Provider updated: {e.provider_updated_at or "unknown"} · Retrieved: {e.retrieved_at} · {e.data_mode}')
                if safe_url(e.source): st.link_button('Open source / API reference',e.source)
                else: st.code(e.source)
                st.json(e.value,expanded=False); st.write(e.limitations)
                if e.conflicts: st.error('Conflicts: '+', '.join(e.conflicts))
                if e.corroborating_ids: st.write('Corroboration: '+', '.join(e.corroborating_ids))

with actions_tab:
    st.subheader('Investor action center')
    for d in companies:
        with st.expander((d.name or d.query)+' · '+d.advice.get('urgency','Review'),expanded=len(companies)==1):
            for step in d.advice.get('next_steps',[]): st.write('• '+step)
            st.markdown('**Hypotheses to test**')
            for h in d.advice.get('hypotheses',[]):
                st.write(h['explanation']); st.caption('Alternative: '+h['alternative']+' · '+', '.join(h['evidence_ids']))
            st.markdown('**Founder follow-up questions**')
            for q in d.advice.get('questions',[]): st.write('• '+q)
            st.text_area('Draft email — never sent',d.advice.get('email',''),height=260,key='email_'+run.id+d.query)
            st.caption(d.advice.get('runway','Runway cannot be estimated from available evidence.'))
    with st.expander('Optional user-supplied runway calculator'):
        st.caption('Local calculation only. Supply company-owned financial data; no cash or burn is inferred from external signals.')
        cash=st.number_input('Cash balance',min_value=0.,value=0.)
        burn=st.number_input('Positive monthly net burn (same currency)',min_value=0.,value=0.)
        financial_date=st.date_input('Financial as-of date')
        if st.button('Calculate supplied runway'):
            try: st.write(f'{runway(cash,burn,financial_date.isoformat()):.1f} months as of {financial_date}. User-supplied, unverified inputs.')
            except ValueError as exc: st.error(str(exc))

with exports:
    st.subheader('A finished briefing. An auditable record.')
    st.write('Download the complete portfolio findings, limitations, decision trail, source attribution and founder follow-up drafts.')
    a,b,c=st.columns(3)
    a.download_button('↓ HTML investor briefing',reports.html(run),f'autopsy-{run.id}.html','text/html',width='stretch')
    b.download_button('↓ Markdown report',reports.markdown(run),f'autopsy-{run.id}.md','text/markdown',width='stretch')
    c.download_button('↓ JSON evidence ledger',reports.ledger(run),f'autopsy-{run.id}.json','application/json',width='stretch')
    st.markdown('**Investigation usage**'); st.json(run.usage,expanded=False)
    st.caption('Cached responses retain original retrieval timestamps. Reports include fetched source material for private research review. No outreach is sent.')
