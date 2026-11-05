"""Decision workspace layered over the existing evidence investigation UI."""
import json
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from autopsy.mandate import Mandate, Workspace, thesis_draft
from autopsy.finance import Deal, Scenario, deal_metrics, readiness, simulate, financing_round
from autopsy.portfolio import allocate, stress
from autopsy.committee import context, review, changes
from autopsy.vcos_reports import export
from autopsy.discovery import search_companies, rows
from autopsy.api import Crustdata, ResearchError
from autopsy.llm import Planner
from autopsy.identity import identify_company,IdentityError,candidate_rows
from autopsy.health import company_health
from autopsy.models import Dossier
from autopsy.evidence import safe_url

NAV=['Overview','Discover','Evaluate','Portfolio Lab','War Room','Investment Committee','Evidence & Reports']


def parsed_editor(label,value,key,height=220):
    if key not in st.session_state: st.session_state[key]=json.dumps(value,indent=2,ensure_ascii=False,default=str)
    return st.text_area(label,key=key,height=height)


def render(settings,store):
    workspace=Workspace()
    if st.session_state.get('requested_section'):
        st.session_state['vcos_section']=st.session_state.pop('requested_section')
    if st.session_state.get('requested_run_id'):
        st.session_state['evidence_run_id']=st.session_state.pop('requested_run_id')
    section=st.sidebar.radio('Workspace',NAV,key='vcos_section')
    saved=workspace.mandates()
    if 'mandate' not in st.session_state and saved:
        st.session_state.mandate=saved[0].model_dump(mode='json')
    mandate=Mandate.model_validate(st.session_state.mandate) if st.session_state.get('mandate') else None
    runs=store.runs()
    if runs:
        if st.session_state.get('evidence_run_id') not in [r.id for r in runs]: st.session_state.pop('evidence_run_id',None)
        run_id=st.sidebar.selectbox('Evidence context',[r.id for r in runs],key='evidence_run_id',format_func=lambda value:next(', '.join(d.name or d.query for d in r.companies)+' · '+r.created_at[:10] for r in runs if r.id==value))
        run=next(r for r in runs if r.id==run_id)
        dossiers={d.company_id:d for d in run.companies if d.company_id and d.status!='duplicate'}
    else: dossiers={}; run=None
    if st.session_state.get('replay_dossiers') is not None:
        dossiers={cid:Dossier.model_validate(d) for cid,d in st.session_state['replay_dossiers'].items()}
        st.sidebar.info('Frozen evidence from decision replay')
        if st.sidebar.button('Return to current evidence'):
            st.session_state.pop('replay_dossiers',None); st.rerun()
    deals=[Deal.model_validate(d) for d in st.session_state.get('vcos_deals',[])]
    if mandate:
        st.sidebar.caption(f'{mandate.name} · {mandate.currency} {mandate.deployable:,.0f} deployable')
    st.caption('DISCOVER → INVESTIGATE → VERIFY → COMPARE → STRESS-TEST → ALLOCATE → CHALLENGE → DECIDE → REPORT')
    if section=='Overview':
        st.subheader('Investment overview')
        metrics=st.columns(4)
        metrics[0].metric('Total portfolio capital',f'{mandate.currency} {mandate.capital:,.0f}' if mandate else 'Set mandate')
        metrics[1].metric('Available after reserves',f'{mandate.currency} {mandate.deployable:,.0f}' if mandate else '—')
        reviews=[readiness(mandate,d,dossiers.get(d.company_id)) for d in deals] if mandate else []
        metrics[2].metric('Deals under evaluation',len(deals))
        metrics[3].metric('Reviewable deals',sum(r['status'] in ('CONDITIONALLY REVIEWABLE','READY FOR COMMITTEE REVIEW') for r in reviews))
        if not mandate: action,target='Review and save your investment mandate.','Overview'
        elif not deals: action,target='Discover opportunities and investigate a shortlist.','Discover'
        elif any(r['violations'] or r['missing'] for r in reviews): action,target='Resolve deal breakers and missing diligence before allocating capital.','Evaluate'
        else: action,target='Compare feasible allocations and challenge the thesis.','Portfolio Lab'
        st.info('Next action: '+action)
        if target!='Overview' and st.button('Open '+target,type='primary'):
            st.session_state['requested_section']=target; st.rerun()
        if mandate:
            st.caption(f'Follow-on reserve: {mandate.currency} {mandate.reserve:,.0f} · Liquidity buffer: {mandate.liquidity_buffer:,.0f} · Outside mandate: {sum(bool(r["violations"]) for r in reviews)} · Require diligence: {sum(bool(r["missing"]) for r in reviews)}')
        st.caption('Capital means total portfolio capital at cost, including existing holdings. Reserve and liquidity are excluded from deployment. Existing private records remain local.')
        mandate_builder(workspace,mandate,saved)
    elif section=='Discover':
        st.subheader('Discover opportunities')
        st.caption('Indexed company search · version 2025-11-01 · 10 results per page · no automatic deep enrichment. Filters use exact provider labels. Search observations do not establish investment readiness.')
        previous_filters=st.session_state.get('discovery_filters',{})
        with st.form('discovery_search_form'):
            a,b,c=st.columns(3)
            industry=a.text_input('Industry label',value=previous_filters.get('industry',''),help='Exact Crustdata industry, e.g. Software Development')
            country=b.text_input('Country label or ISO alpha-3',value=previous_filters.get('country',''),help='For example IND; country means indexed company locations, not necessarily domicile.')
            stage=c.text_input('Funding round type',value=previous_filters.get('stage',''),help='Exact provider label, e.g. series_a')
            a,b=st.columns(2)
            head=a.number_input('Minimum headcount',min_value=0,value=int(previous_filters.get('min_headcount',0)))
            growth=b.text_input('Minimum 6m headcount growth % (optional)',value=str(previous_filters.get('growth')) if previous_filters.get('growth') is not None else '')
            refresh=st.checkbox('Refresh discovery data',help='Bypass the response cache for this explicit search. Existing investigation histories are retained.')
            search=st.form_submit_button('Search Crustdata',disabled=not settings.api_key,type='primary')
        filters=dict(industry=industry,country=country,stage=stage,min_headcount=head,growth=float(growth) if growth.strip() and _is_number(growth) else None)
        if search:
            if growth.strip() and not _is_number(growth): st.error('Growth must be a number')
            else: discovery_request(settings,store,filters,refresh=refresh)
        page=st.session_state.get('discovery_page')
        if page:
            if st.session_state.get('discovery_error'):
                st.warning('The latest search failed. Showing the previous successful result page with its original filters and retrieval date.')
            st.caption(f'{page["mode"]} · retrieved {page["retrieved_at"]} · why included: {json.dumps(page["filters"])}')
            table=rows(page,mandate)
            query=st.text_input('Search this result page')
            st.dataframe(pd.DataFrame([r for r in table if query.casefold() in str(r).casefold()]),hide_index=True,width='stretch')
            options=[r['Domain'] for r in table if r['Domain']]
            selected=st.multiselect('Shortlist 2–5 companies for deep diligence',options,max_selections=5)
            if selected: st.session_state['shortlist_text']='\n'.join(selected)
            st.caption('Selected domains populate the investigation input below. Launch explicitly to spend enrichment credits.')
            if st.button('Add selected to evaluation',disabled=not selected,type='primary'):
                pool=st.session_state.get('evaluation_pool',{})
                for row in table:
                    if row['Domain'] in selected and row['ID']:
                        pool[row['ID']]={'name':row['Company'],'domain':row['Domain']}
                if len(pool)>5: st.error('Keep at most five evaluation candidates. Remove existing opportunities before adding more.')
                else:
                    st.session_state['evaluation_pool']=pool
                    st.session_state['requested_section']='Evaluate'; st.rerun()
            if page.get('next_cursor') and st.button('Next search page'):
                discovery_request(settings,store,st.session_state['discovery_filters'],page['next_cursor']); st.rerun()
            name=st.text_input('Watchlist name')
            if st.button('Save named watchlist',disabled=not bool(name and selected)):
                workspace.save('watchlists',{'name':name,'domains':selected,'source':'Crustdata search','retrieved_at':page['retrieved_at']}); st.success('Watchlist saved locally')
        watchlists=workspace.list('watchlists')
        if watchlists:
            with st.expander('Saved watchlists'):
                chosen=st.selectbox('Watchlist',range(len(watchlists)),format_func=lambda i:watchlists[i]['name'])
                st.write(watchlists[chosen]['domains'])
                if st.button('Use watchlist for investigation'):
                    st.session_state['shortlist_text']='\n'.join(watchlists[chosen]['domains']); st.rerun()
        st.divider()
        st.subheader('Investigate your shortlist')
        identity_controls(settings,store)
        return section
    elif section=='Evaluate':
        st.subheader('Deal comparison arena')
        st.caption('Enter supplied terms in mandate currency. Unknown values stay blank. Financials are annual revenue and current monthly net burn; no company metrics are prefilled.')
        if not mandate: st.info('Save a mandate in Overview first.'); return section
        pool={cid:Dossier(query=item['domain'],company_id=cid,name=item['name'] or item['domain'],domain=item['domain']) for cid,item in st.session_state.get('evaluation_pool',{}).items()}
        available=pool|dossiers
        options=list(available)
        defaults=list(dict.fromkeys([d.company_id for d in deals if d.company_id in options]+list(pool)))[:5]
        selected=st.multiselect('Companies from evidence context',options,default=defaults,format_func=lambda cid:available[cid].name or available[cid].query,max_selections=5)
        if pool and any(cid not in dossiers for cid in selected):
            st.info('Discovery candidates are selected for evaluation. Launch their dossier investigations in Discover before an allocation can become reviewable.')
            if st.button('Investigate evaluation candidates'):
                st.session_state['shortlist_text']='\n'.join(available[cid].domain for cid in selected)
                st.session_state['requested_section']='Discover'; st.rerun()
        manual=st.text_area('Or add company domains for a terms-only comparison',help='One per line; no external evidence is implied. Up to five combined companies.')
        manual_ids=[x.strip().lower() for x in manual.splitlines() if x.strip()]
        ids=list(dict.fromkeys(selected+manual_ids))
        if len(ids)>5: st.error('Select at most five companies'); return section
        previous={d.company_id:d.model_dump(mode='json') for d in deals}
        templates=[]
        for cid in ids:
            templates.append(previous.get(cid,{'company_id':cid,'name':dossiers[cid].name if cid in dossiers else cid,
                'currency':mandate.currency,'sector':'','stage':'','geography':'','investment':0,'valuation':0,
                'valuation_basis':'pre-money','round_size':None,'instrument':'Ordinary equity','cash':None,
                'monthly_burn':None,'revenue':None,'financial_date':None,'documents':[],
                'rejection_reviewed':False,'downside_moic':None,'base_moic':None,'upside_moic':None}))
        if ids:
            with st.expander('Guided deal editor',expanded=True):
                cid=st.selectbox('Edit opportunity',ids,format_func=lambda value:available[value].name if value in available else value)
                guided_deal_editor(cid,mandate,available,previous)
        if st.button('Prepare editable deal terms',disabled=not ids):
            st.session_state['terms_json']=json.dumps(templates,indent=2,ensure_ascii=False)
        if 'terms_json' in st.session_state:
            with st.expander('Advanced deal terms · JSON'):
                with st.form('deal_terms'):
                    raw=st.text_area('Deal terms · editable JSON',key='terms_json',height=370)
                    st.caption('Required document attestations: Financial statements, Cap table, Term sheet. These labels do not verify contents. Return MOIC values are user-modeled assumptions. Supported financial_date: YYYY-MM-DD. Leave unknown financials null. All terms remain reviewable.')
                    submit=st.form_submit_button('Validate and compare',type='primary')
            if submit:
                try:
                    parsed=json.loads(raw)
                    if not isinstance(parsed,list) or not 1<=len(parsed)<=5: raise ValueError('Supply 1–5 deal objects')
                    new=[Deal.model_validate(item) for item in parsed]
                    if len({d.company_id for d in new})!=len(new): raise ValueError('Duplicate company identities')
                    st.session_state['vcos_deals']=[d.model_dump(mode='json') for d in new]
                    st.session_state.pop('allocation',None); st.session_state.pop('committee',None)
                    deals=new
                except (ValueError,TypeError) as exc: st.error(str(exc))
        comparison(mandate,deals,dossiers)
    elif section=='Portfolio Lab':
        st.subheader('Conditional capital allocation')
        if not mandate or not deals: st.info('Save a mandate and deal terms first.'); return section
        st.caption('Scenario optimization compares deployment with holding cash at 1x nominal value. Conservative uses downside, Moderate uses worst-case across scenarios, Aggressive uses base. Missing financial evidence excludes a deal; the solver may allocate zero.')
        strategy=st.selectbox('Scenario objective',['robust','downside','base'],index={'Conservative':1,'Moderate':0,'Aggressive':2}[mandate.risk])
        if st.button('Compute allocation & alternatives',type='primary'):
            try:
                result=allocate(mandate,deals,dossiers,strategy)
                st.session_state['allocation']=result
                st.session_state['allocation_context']=fingerprint(mandate,deals,dossiers)
                st.session_state['alternatives']=[allocate(mandate,deals,dossiers,s) for s in ('downside','base','robust') if s!=strategy]
            except ValueError as exc: st.error(str(exc))
        result=current_allocation(mandate,deals,dossiers)
        if result:
            a,b,c=st.columns(3)
            a.metric('New deployment',f'{sum(result["allocations"].values()):,.0f}')
            b.metric('Uninvested deployment budget',f'{result["uninvested"]:,.0f}')
            c.metric('Follow-on reserve',f'{result["reserve"]:,.0f}')
            st.write(result['reason'])
            st.dataframe(pd.DataFrame([{'Company':d.name,'Conditional allocation':result['allocations'][d.company_id],
                                      'Reason':'; '.join(result['excluded'].get(d.company_id,[])) or result['reason']} for d in deals]),hide_index=True,width='stretch')
            if result['violations']: st.error('; '.join(result['violations']))
            a,b=st.columns(2)
            for column,field in [(a,'sector_exposure'),(b,'stage_exposure')]:
                frame=pd.DataFrame([{'Category':k,'Capital at cost':v} for k,v in result[field].items()])
                if not frame.empty and frame['Capital at cost'].sum()>0:
                    column.plotly_chart(px.bar(frame,x='Category',y='Capital at cost',title=field.replace('_',' ').title(),color_discrete_sequence=['#58dac2']),width='stretch')
            with st.expander('Alternative feasible strategies'):
                st.dataframe(pd.DataFrame([{'Objective':a['strategy'],'Allocated':sum(a['allocations'].values()),'Uninvested':a['uninvested'],'Reserve':a['reserve'],'Explanation':a['reason']} for a in st.session_state.get('alternatives',[])]),hide_index=True,width='stretch')
            with st.expander('Stress new allocations'):
                compression=st.slider('Exit outcome multiplier',0.,2.,.7,.05)
                failed=st.multiselect('Company failure / zero recovery',[d.company_id for d in deals],format_func=lambda cid:next(d.name for d in deals if d.company_id==cid))
                if all(d.base_moic is not None for d in deals):
                    scenario=stress(result['allocations'],deals,compression,failed)
                    st.dataframe(pd.DataFrame(scenario['holdings']),hide_index=True)
                    st.write('Modeled capital at risk:',scenario['capital_at_risk']); st.caption(scenario['label'])
                else: st.info('Supply base MOIC assumptions for every deal before stress testing.')
    elif section=='War Room':
        war_room(workspace)
    elif section=='Investment Committee':
        st.subheader('Investment committee challenge')
        if not mandate or not deals: st.info('Save a mandate and deal terms first.'); return section
        allocation=current_allocation(mandate,deals,dossiers)
        try: ctx=context(mandate,deals,dossiers,allocation)
        except ValueError as exc:
            st.error('Decision evidence validation failed: '+str(exc)); return section
        ctx['war_room']=st.session_state.get('war_outcomes')
        comparison(mandate,deals,dossiers)
        st.caption('One Gemini provider, three structured role passes. Failed calls or invalid references produce visibly labeled deterministic checklists. Final readiness comes from deterministic rules, not AI approval.')
        if st.button('Challenge investment thesis',type='primary'):
            planner=Planner(settings)
            try:
                with st.spinner('Reviewing evidence and supplied assumptions'):
                    st.session_state['committee']=review(ctx,planner)
                    st.session_state['committee_context']=context_fingerprint(ctx)
            finally: planner.close()
        committee=st.session_state.get('committee') if st.session_state.get('committee_context')==context_fingerprint(ctx) else None
        if committee:
            st.caption('Analysis engine: '+committee['engine'])
            st.info('AI-generated hypotheses and draft questions. Factual findings and calculations remain linked to the ledger and deterministic tables.')
            for perspective in committee['perspectives']:
                with st.expander(perspective['role']+' · '+perspective['engine'],expanded=True):
                    for item in perspective['thesis']+perspective['challenges']:
                        st.write(item['claim']); st.caption('Hypothesis / challenge · References: '+', '.join(item['references']))
                    for question in perspective['questions']: st.write(question)
            for diagnostic in committee['diagnostics']: st.warning(diagnostic)
            with st.expander('Provider, model and generation diagnostics'):
                st.json(committee.get('provider_diagnostics',{}))
        st.markdown('**Decision memo exports**')
        try: artifacts=export(ctx,committee)
        except ValueError as exc:
            st.error('Memo validation failed; export withheld: '+str(exc)); return section
        a,b,c=st.columns(3)
        for col,extension,mime in [(a,'html','text/html'),(b,'md','text/markdown'),(c,'json','application/json')]:
            col.download_button('Download '+extension.upper()+' memo',artifacts[extension],'vcos-committee.'+extension,mime)
        if st.button('Save decision snapshot'):
            workspace.save('snapshots',{'kind':'decision','context':ctx,'committee':committee}); st.success('Decision snapshot saved locally')
        decision_replay(workspace)
    elif section=='Evidence & Reports':
        st.subheader('Evidence, provenance & investigation history')
        if run:
            st.caption('Execution: '+('COMPLETED' if run.status=='complete' else run.status.upper())+' · Engine: '+run.usage.get('analysis_engine','Legacy run: see decision trace')+' · '+run.mode)
            st.caption('Evidence coverage is a separate measurement. Decision confidence is uncalibrated; committee readiness requires primary financial and legal review.')
            st.dataframe(pd.DataFrame([{'Company':d.name or d.query,**{k:v for k,v in company_health(d).items() if k in ('execution','coverage_percent','verification','latest_observation','provider_updated_at','retrieved_at')}} for d in run.companies]),hide_index=True,width='stretch')
            for d in run.companies:
                if d.errors: st.warning((d.name or d.query)+': '+'; '.join(d.errors))
            with st.expander('Model generation diagnostics · recorded for this investigation'):
                st.json(run.usage.get('llm_diagnostics',{'status':'Legacy run; inspect original trace and diagnostics'}))
        return section
    return section


def mandate_builder(workspace,mandate,saved):
    st.subheader('Investment mandate & thesis')
    if saved:
        selected=st.selectbox('Saved mandates',range(len(saved)),format_func=lambda i:saved[i].name+' · '+saved[i].id[:6])
        if st.button('Load reviewed mandate'):
            st.session_state.mandate=saved[selected].model_dump(mode='json')
            st.session_state.pop('mandate_json',None); st.rerun()
    thesis=st.text_area('Describe your investment goals',placeholder='I have ₹10 crore, want Indian B2B SaaS startups, moderate risk, a 5-year horizon, maximum 25% in any company, and 30% reserved for follow-on funding.')
    if st.button('Draft constraints from thesis',disabled=not thesis):
        draft=mandate.model_dump(mode='json') if mandate else Mandate(capital=1e8).model_dump(mode='json')
        draft.update(thesis_draft(thesis))
        st.session_state['mandate_json']=json.dumps(draft,indent=2,ensure_ascii=False)
        st.session_state['thesis_diagnostic']='Deterministic extraction. Review all fields; unrecognized goals remain in the thesis and require manual constraints. Draft defaults are editable, not inferred preferences.'
    if st.session_state.get('thesis_diagnostic'): st.info(st.session_state.thesis_diagnostic)
    with st.expander('Guided mandate editor',expanded=not bool(mandate)):
        try:
            initial=Mandate.model_validate_json(st.session_state['mandate_json']).model_dump(mode='json') if st.session_state.get('mandate_json') else (mandate.model_dump(mode='json') if mandate else Mandate(capital=1e8).model_dump(mode='json'))
        except ValueError:
            initial=mandate.model_dump(mode='json') if mandate else Mandate(capital=1e8).model_dump(mode='json')
        with st.form('guided_mandate'):
            a,b,c=st.columns(3)
            name=a.text_input('Mandate name',value=initial.get('name','Investment mandate'))
            capital=b.number_input('Total portfolio capital',min_value=1.,value=max(1.,float(initial.get('capital',1e8))))
            currency=c.text_input('Currency (ISO code)',value=initial.get('currency','INR'))
            a,b=st.columns(2)
            risk=a.selectbox('Risk tolerance',['Conservative','Moderate','Aggressive'],index=['Conservative','Moderate','Aggressive'].index(initial.get('risk','Moderate')))
            horizon=b.number_input('Investment horizon (years)',min_value=1,max_value=30,value=max(1,min(30,initial.get('horizon_years',5))))
            a,b,c=st.columns(3)
            sectors=a.text_input('Sector preferences (comma separated)',value=', '.join(initial.get('sectors',[])))
            stages=b.text_input('Stage preferences (comma separated)',value=', '.join(initial.get('stages',[])))
            geographies=c.text_input('Geographic preferences (comma separated)',value=', '.join(initial.get('geographies',[])))
            a,b=st.columns(2)
            minimum=a.number_input('Minimum cheque',min_value=0.,value=max(0.,float(initial.get('min_cheque',0))))
            maximum=b.number_input('Maximum cheque',min_value=1.,value=max(1.,float(initial.get('max_cheque',1e8))))
            a,b,c=st.columns(3)
            company=a.number_input('Maximum company exposure %',min_value=.1,max_value=100.,value=max(.1,min(100.,initial.get('company_limit',.25)*100)))
            sector=b.number_input('Maximum sector exposure %',min_value=.1,max_value=100.,value=max(.1,min(100.,initial.get('sector_limit',.5)*100)))
            stage=c.number_input('Maximum stage exposure %',min_value=.1,max_value=100.,value=max(.1,min(100.,initial.get('stage_limit',.75)*100)))
            a,b=st.columns(2)
            reserve=a.number_input('Follow-on reserve %',min_value=0.,max_value=100.,value=max(0.,min(100.,initial.get('reserve_fraction',.3)*100)))
            liquidity=b.number_input('Liquidity buffer',min_value=0.,value=max(0.,float(initial.get('liquidity_buffer',0))))
            apply=st.form_submit_button('Save reviewed mandate',type='primary')
        if apply:
            initial.update(name=name,capital=capital,currency=currency.upper().strip(),risk=risk,horizon_years=horizon,
                sectors=_csv(sectors),stages=_csv(stages),geographies=_csv(geographies),min_cheque=minimum,max_cheque=maximum,
                company_limit=company/100,sector_limit=sector/100,stage_limit=stage/100,reserve_fraction=reserve/100,liquidity_buffer=liquidity)
            try:
                from uuid import uuid4
                reviewed=Mandate.model_validate(initial).model_copy(update={'id':uuid4().hex})
                workspace.save('mandates',reviewed.model_dump(mode='json'))
                st.session_state['mandate']=reviewed.model_dump(mode='json')
                st.session_state['mandate_json']=reviewed.model_dump_json(indent=2)
                st.rerun()
            except ValueError as exc: st.error(str(exc))
    with st.expander('Advanced constraints · holdings, ownership, rejection criteria & JSON'):
        with st.form('mandate_form'):
            initial=mandate.model_dump(mode='json') if mandate else Mandate(capital=1e8).model_dump(mode='json')
            raw=parsed_editor('Review every mandate constraint · editable JSON',initial,'mandate_json',350)
            st.caption('capital = total portfolio budget including existing holdings; existing = [{company_id, sector, stage, amount}]. Limits and reserve_fraction use fractions (0.25 = 25%). Empty preference lists allow any. Custom rejection criteria require an explicit per-deal review. Saved constraints are never changed by the LLM.')
            submit=st.form_submit_button('Validate & save mandate',type='primary')
    if submit:
        try:
            value=Mandate.model_validate_json(raw)
            # Keep earlier reviewed mandates loadable instead of overwriting them.
            from uuid import uuid4
            value=value.model_copy(update={'id':uuid4().hex})
            workspace.save('mandates',value.model_dump(mode='json'))
            st.session_state.mandate=value.model_dump(mode='json')
            st.success(f'Saved {value.name}: {value.currency} {value.deployable:,.0f} deployable; {value.reserve:,.0f} reserved. All hard limits enforced.')
        except ValueError as exc: st.error(str(exc))


def comparison(mandate,deals,dossiers):
    if not deals: st.info('Select at least two companies and supply terms to compare.'); return
    table=[]
    for d in deals:
        metrics=deal_metrics(d); result=readiness(mandate,d,dossiers.get(d.company_id))
        dossier=dossiers.get(d.company_id)
        health=company_health(dossier) if dossier else {}
        table.append({'Company':d.name,'Readiness':result['status'],'Proposed investment':d.investment,
                      'Post-money':metrics['post_money'],'Ownership %':metrics['ownership']*100 if metrics['ownership'] is not None else None,
                      'Post-money / annual revenue':metrics['valuation_revenue_multiple'],'Runway months':metrics['runway_months'],
                      'Revenue growth %':metrics['revenue_growth']*100 if metrics['revenue_growth'] is not None else None,
                      'Gross margin':metrics['gross_margin'],'Operating margin':metrics['operating_margin'],
                      'Evidence coverage %':dossier.assessment.coverage if dossier else None,
                      'Evidence verification':health.get('verification','Unknown'),
                      'Latest observation':health.get('latest_observation') or 'Unknown',
                      'Provider update':health.get('provider_updated_at') or 'Unknown',
                      'API retrieval':health.get('retrieved_at') or 'No evidence retrieved',
                      'Team / operating signals':'; '.join(s.explanation+' ['+', '.join(s.evidence_ids)+']' for s in dossier.assessment.signals) if dossier else 'Unknown',
                      'Missing diligence':'; '.join(result['missing']),'Mandate violations':'; '.join(result['violations'])})
    frame=pd.DataFrame(table).set_index('Company').T
    st.dataframe(frame.where(pd.notna(frame),'Unknown'),width='stretch')
    st.caption('Valuation attractiveness depends on supplied revenue, growth and outcome assumptions; workforce and funding do not determine a ranking. Neither deal may be suitable. Financial sustainability and leadership stability remain unknown where primary evidence is missing.')
    for d in deals:
        with st.expander(d.name+' · calculation assumptions & terms'):
            st.json(deal_metrics(d)); st.caption(d.provenance)
            dossier=dossiers.get(d.company_id)
            if dossier:
                ids={ref for signal in dossier.assessment.signals for ref in signal.evidence_ids}
                observations=[{'Evidence ID':e.id,'Observation':e.observation_date or e.event_date,'Value':e.value,
                    'Verification':e.status,'Source':e.source if safe_url(e.source) else None,'Retrieved':e.retrieved_at} for e in dossier.evidence if e.id in ids]
                if observations:
                    st.dataframe(pd.DataFrame(observations),hide_index=True,width='stretch',
                        column_config={'Source':st.column_config.LinkColumn('Source / API reference')})


def guided_deal_editor(cid,mandate,dossiers,previous):
    initial=previous.get(cid,{})
    with st.form('guided_deal_'+cid):
        a,b,c=st.columns(3)
        sector=a.text_input('Company sector',value=initial.get('sector',''))
        stage=b.text_input('Investment stage',value=initial.get('stage',''))
        geography=c.text_input('Company geography',value=initial.get('geography',''))
        a,b,c=st.columns(3)
        investment=a.number_input('Proposed cheque',min_value=0.,value=float(initial.get('investment',0)))
        valuation=b.number_input('Entry valuation',min_value=0.,value=float(initial.get('valuation',0)))
        basis=c.selectbox('Valuation basis',['pre-money','post-money'],index=int(initial.get('valuation_basis')=='post-money'))
        a,b=st.columns(2)
        round_size=a.number_input('Total round size (0 = unknown)',min_value=0.,value=float(initial.get('round_size') or 0))
        instruments=['Ordinary equity','Preferred shares','SAFE','Convertible note']
        instrument=b.selectbox('Security / instrument',instruments,index=instruments.index(initial.get('instrument','Ordinary equity')))
        provenance_options=['USER-PROVIDED DATA','MODELED ASSUMPTIONS','SYNTHETIC DEMO DATA']
        provenance=st.selectbox('Investment input provenance',provenance_options,index=provenance_options.index(initial.get('provenance','USER-PROVIDED DATA')),
            help='Use MODELED ASSUMPTIONS for illustrative terms or hypothetical financials. This label never changes the provenance of external company evidence.')
        financials=st.checkbox('I am supplying dated company financials',value=initial.get('cash') is not None)
        a,b,c=st.columns(3)
        cash=a.number_input('Supplied cash balance',min_value=0.,value=float(initial.get('cash') or 0))
        burn=b.number_input('Supplied monthly net burn',min_value=0.,value=float(initial.get('monthly_burn') or 0))
        revenue=c.number_input('Supplied annual revenue',min_value=0.,value=float(initial.get('revenue') or 0))
        financial_date=st.date_input('Financial data as-of',value=date.fromisoformat(initial['financial_date']) if initial.get('financial_date') else date.today(),max_value=date.today())
        documents=st.multiselect('Documents supplied · user attestation',['Financial statements','Cap table','Term sheet'],default=[d for d in initial.get('documents',[]) if d in ('Financial statements','Cap table','Term sheet')])
        rejection_reviewed=st.checkbox('I reviewed all custom hard rejection criteria',value=initial.get('rejection_reviewed',False))
        human_review=st.checkbox('I completed primary document verification for committee review',value=initial.get('human_review_confirmed',False))
        has_outcomes=st.checkbox('Supply modeled outcome MOIC assumptions',value=initial.get('base_moic') is not None)
        a,b,c=st.columns(3)
        down=a.number_input('Downside MOIC assumption',min_value=0.,value=float(initial.get('downside_moic') or 0))
        base=b.number_input('Base MOIC assumption',min_value=0.,value=float(initial.get('base_moic') or 0))
        up=c.number_input('Upside MOIC assumption',min_value=0.,value=float(initial.get('upside_moic') or 0))
        submit=st.form_submit_button('Validate & save opportunity',type='primary')
    if submit:
        try:
            d=Deal(**(initial|dict(company_id=cid,name=dossiers[cid].name if cid in dossiers else cid,
                currency=mandate.currency,sector=sector,stage=stage,geography=geography,investment=investment,
                valuation=valuation,valuation_basis=basis,round_size=round_size or None,instrument=instrument,
                provenance=provenance,
                cash=cash if financials else None,monthly_burn=burn if financials else None,
                revenue=revenue if financials else None,financial_date=financial_date if financials else None,
                documents=documents,rejection_reviewed=rejection_reviewed,human_review_confirmed=human_review,
                downside_moic=down if has_outcomes else None,base_moic=base if has_outcomes else None,upside_moic=up if has_outcomes else None)))
            updated={v['company_id']:v for v in st.session_state.get('vcos_deals',[])}
            updated[cid]=d.model_dump(mode='json')
            if len(updated)>5: raise ValueError('At most five opportunities; edit the JSON list to remove unused deals')
            st.session_state['vcos_deals']=list(updated.values())
            st.session_state['terms_json']=json.dumps(list(updated.values()),indent=2,ensure_ascii=False)
            st.session_state.pop('allocation',None); st.session_state.pop('committee',None)
            st.success('Opportunity saved. Comparison updated below.'); st.rerun()
        except ValueError as exc: st.error(str(exc))


def war_room(workspace):
    if st.session_state.get('replay_scenario_inputs'):
        restored=st.session_state.pop('replay_scenario_inputs')
        st.session_state.update(restored)
        st.session_state['war_inputs']=restored
        st.session_state['war_started']=True
    for key,value in st.session_state.get('war_inputs',{}).items():
        if key not in st.session_state: st.session_state[key]=value
    st.subheader('VC War Room')
    st.caption('MODELED ASSUMPTIONS · deterministic cash flows and ordinary-equity outcomes · not validated forecasts. Enter inputs in one currency. No provider financial values are inferred.')
    st.caption('Cash flows recalculate immediately as inputs change. Allocation changes require explicitly applying the modeled outcomes to a matching opportunity below.')
    with st.container(border=True):
        a,b,c=st.columns(3)
        cash=a.number_input('Available cash',min_value=0.,value=0.,key='war_cash')
        burn=b.number_input('Monthly net burn',min_value=0.,value=0.,key='war_burn')
        years=c.selectbox('Horizon in years',[1,3,5,7,10],index=2,key='war_years')
        a,b,c=st.columns(3)
        reduction=a.slider('Net burn reduction %',0,100,0,key='war_reduction')
        implementation=b.number_input('One-time implementation cost',min_value=0.,value=0.,key='war_implementation')
        revenue=c.number_input('Current monthly revenue',min_value=0.,value=0.,key='war_revenue')
        a,b,c=st.columns(3)
        growth=a.number_input('Monthly revenue growth %',min_value=-100.,max_value=100.,value=0.,key='war_growth')
        financing=b.number_input('Financing amount',min_value=0.,value=0.,key='war_financing')
        month=c.number_input('Financing at start of month',min_value=1,max_value=120,value=1,key='war_month')
        a,b,c=st.columns(3)
        ownership=a.number_input('Current ownership %',min_value=0.,max_value=100.,value=0.,key='war_ownership')
        dilution=b.number_input('Dilution upon financing %',min_value=0.,max_value=100.,value=0.,key='war_dilution')
        invested=c.number_input('Total investor cost basis',min_value=0.,value=0.,key='war_invested')
        a,b,c=st.columns(3)
        downside=a.number_input('Downside exit value',min_value=0.,value=0.,key='war_downside')
        base=b.number_input('Base exit value',min_value=0.,value=0.,key='war_base')
        upside=c.number_input('Upside exit value',min_value=0.,value=0.,key='war_upside')
        submit=st.button('Run scenario comparison',type='primary')
    keys=['war_cash','war_burn','war_years','war_reduction','war_implementation','war_revenue','war_growth','war_financing','war_month','war_ownership','war_dilution','war_invested','war_downside','war_base','war_upside']
    st.session_state['war_inputs']={key:st.session_state[key] for key in keys}
    if submit or st.session_state.get('war_started') or cash>0 or burn>0:
        if not downside<=base<=upside:
            st.session_state.pop('war_outcomes',None)
            st.error('Exit scenarios require downside <= base <= upside.'); return
        try:
            s=Scenario(cash=cash,monthly_burn=burn,years=years,burn_reduction=reduction/100,
                implementation_cost=implementation,monthly_revenue=revenue,monthly_revenue_growth=growth/100,
                financing=financing,financing_month=month,ownership=ownership/100,dilution=dilution/100,invested=invested,exit_value=base)
            outcomes={name:simulate(s.model_copy(update={'exit_value':value})) for name,value in [('Downside',downside),('Base',base),('Upside',upside),('Capital loss',0.)]}
            outcomes['Baseline cash']=simulate(s.model_copy(update={'burn_reduction':0.,'implementation_cost':0.,'financing':0.,'monthly_revenue_growth':0.}))
            st.session_state['war_outcomes']=outcomes
            st.session_state['war_started']=True
            st.session_state['war_sensitivity']=[{'Financing month':m,'Exhaustion month':simulate(s.model_copy(update={'financing_month':m}))['cash_exhaustion_month']} for m in range(1,min(25,12*years+1))]
        except ValueError as exc:
            st.session_state.pop('war_outcomes',None); st.error(str(exc)); return
    outcomes=st.session_state.get('war_outcomes')
    if outcomes:
        base_case=outcomes['Base']
        a,b,c,d=st.columns(4)
        a.metric('Baseline runway',f'{base_case["baseline_runway_months"]:.1f} months' if base_case['baseline_runway_months'] is not None else 'No net burn')
        b.metric('Cash exhaustion',f'Month {base_case["cash_exhaustion_month"]}' if base_case['cash_exhaustion_month'] is not None else 'Survives horizon')
        c.metric('Base MOIC',f'{base_case["moic"]:.2f}×' if base_case['moic'] is not None else 'Cost basis required')
        d.metric('Ending ownership',f'{base_case["ending_ownership"]:.2%}')
        st.dataframe(pd.DataFrame([{'Scenario':name,**{k:v for k,v in out.items() if k not in ('trajectory','assumptions','limitations')}} for name,out in outcomes.items()]),hide_index=True,width='stretch')
        trajectories=[{**point,'Scenario':name} for name,out in outcomes.items() if name in ('Base','Baseline cash') for point in out['trajectory']]
        st.plotly_chart(px.line(pd.DataFrame(trajectories),x='month',y='cash',color='Scenario',color_discrete_map={'Base':'#58dac2','Baseline cash':'#93a5bd'}),width='stretch')
        sensitivity=pd.DataFrame(st.session_state.get('war_sensitivity',[]))
        st.caption('Funding delay sensitivity · blank exhaustion means cash survives the modeled horizon.')
        st.dataframe(sensitivity,hide_index=True)
        with st.expander('All supplied assumptions and model conventions'): st.json(outcomes['Base']['assumptions']); st.write(outcomes['Base']['limitations'])
        if st.button('Save scenario snapshot'):
            workspace.save('snapshots',{'kind':'scenario','outcomes':outcomes}); st.success('Scenario saved')
        scenario_to_opportunity(outcomes)
    with st.expander('Cap table & follow-on planner'):
        st.caption('Ordinary equity only. One financing round per calculation. No SAFEs, notes, preferred liquidation or participation rights. Pool fraction is newly issued post-financing ownership.')
        a,b=st.columns(2)
        own=a.number_input('Ownership before round %',0.,100.,0.)
        pre=b.number_input('Round pre-money valuation',min_value=1.,value=1.)
        amount=a.number_input('Total new financing',min_value=0.,value=0.)
        follow=b.number_input('Your follow-on participation',min_value=0.,value=0.)
        pool=a.number_input('New post-round option pool %',0.,99.,0.)
        if st.button('Calculate dilution & reserve required'):
            try:
                result=financing_round(own/100,pre,amount,follow,pool/100)
                st.json(result)
                if st.session_state.get('mandate'):
                    reserve=Mandate.model_validate(st.session_state.mandate).reserve
                    st.write('Modeled reserve shortfall for maintaining this ownership:',max(0.,result['capital_to_maintain_after_pool']-reserve))
                    st.caption('Single supplied round only; other portfolio follow-on needs are not included.')
            except ValueError as exc: st.error(str(exc))
    decision_replay(workspace)


def scenario_to_opportunity(outcomes):
    deals=[Deal.model_validate(d) for d in st.session_state.get('vcos_deals',[])]
    if not deals: return
    with st.expander('Apply modeled outcomes to an opportunity'):
        cid=st.selectbox('Opportunity for these modeled outcomes',[d.company_id for d in deals],format_func=lambda value:next(d.name for d in deals if d.company_id==value))
        deal=next(d for d in deals if d.company_id==cid)
        inputs=outcomes['Base']['assumptions']
        metrics=deal_metrics(deal)
        matching=(metrics['ownership'] is not None and abs(inputs['ownership']-metrics['ownership'])<1e-8 and abs(inputs['invested']-deal.investment)<.01 and deal.investment>0)
        st.caption('Requires ordinary-equity entry ownership and cost basis matching the supplied opportunity. Applying outcomes changes modeled MOIC only; it does not overwrite financial evidence or legal terms.')
        if not matching: st.warning('Match current ownership and total investor cost basis to this opportunity before applying outcomes.')
        confirmed=st.checkbox('I confirm these modeled assumptions apply to this opportunity')
        if st.button('Apply outcomes and invalidate prior allocation',disabled=not (matching and confirmed)):
            values={'downside_moic':outcomes['Downside']['moic'],'base_moic':outcomes['Base']['moic'],'upside_moic':outcomes['Upside']['moic']}
            revised=Deal.model_validate(deal.model_dump(mode='json')|values)
            st.session_state['vcos_deals']=[revised.model_dump(mode='json') if d.company_id==cid else d.model_dump(mode='json') for d in deals]
            for key in ('allocation','committee','terms_json'): st.session_state.pop(key,None)
            st.success('Modeled outcomes applied. Recompute the conditional allocation in Portfolio Lab; previous saved decisions remain unchanged.')


def decision_replay(workspace):
    snapshots=workspace.list('snapshots')
    if not snapshots: return
    with st.expander('Decision replay · actual before / after changes'):
        selected=st.selectbox('Prior snapshot',range(len(snapshots)),format_func=lambda i:snapshots[i]['created_at']+' · '+snapshots[i].get('kind','decision'))
        prior=snapshots[selected]
        st.json(prior,expanded=False)
        if st.button('Reopen prior scenario / decision'):
            if prior.get('kind')=='scenario':
                st.session_state['war_outcomes']=prior['outcomes']
                st.session_state['war_sensitivity']=[]
                s=prior['outcomes']['Base']['assumptions']
                st.session_state['replay_scenario_inputs']={'war_cash':s['cash'],'war_burn':s['monthly_burn'],'war_years':s['years'],
                    'war_reduction':round(s['burn_reduction']*100),'war_implementation':s['implementation_cost'],
                    'war_revenue':s['monthly_revenue'],'war_growth':s['monthly_revenue_growth']*100,
                    'war_financing':s['financing'],'war_month':s['financing_month'],'war_ownership':s['ownership']*100,
                    'war_dilution':s['dilution']*100,'war_invested':s['invested'],
                    'war_downside':prior['outcomes']['Downside']['assumptions']['exit_value'],
                    'war_base':s['exit_value'],'war_upside':prior['outcomes']['Upside']['assumptions']['exit_value']}
            else:
                st.session_state['mandate']=prior['context']['mandate']
                st.session_state['vcos_deals']=[d['terms'] for d in prior['context']['deals']]
                st.session_state['replay_dossiers']=prior['context'].get('dossiers',{})
                for key in ('terms_json','mandate_json','committee','allocation'): st.session_state.pop(key,None)
                from autopsy.models import Dossier
                frozen={cid:Dossier.model_validate(d) for cid,d in st.session_state['replay_dossiers'].items()}
                restored_mandate=Mandate.model_validate(st.session_state['mandate'])
                restored_deals=[Deal.model_validate(d) for d in st.session_state['vcos_deals']]
                st.session_state['allocation']=prior['context'].get('allocation')
                st.session_state['allocation_context']=fingerprint(restored_mandate,restored_deals,frozen)
                st.session_state['war_outcomes']=prior['context'].get('war_room')
                if st.session_state['war_outcomes']:
                    st.session_state['replay_scenario_inputs']=scenario_widget_values(st.session_state['war_outcomes'])
                else:
                    st.session_state['war_inputs']={}
                    st.session_state['war_started']=False
                    for key in ('war_cash','war_burn','war_years','war_reduction','war_implementation','war_revenue','war_growth','war_financing','war_month','war_ownership','war_dilution','war_invested','war_downside','war_base','war_upside'):
                        st.session_state.pop(key,None)
                st.session_state['committee']=prior.get('committee')
                st.session_state['committee_context']=context_fingerprint(prior['context'])
                st.session_state['requested_section']='Investment Committee'
            st.rerun()
        if len(snapshots)>1:
            other=st.selectbox('Compare with snapshot',range(len(snapshots)),index=1 if selected==0 else 0,format_func=lambda i:snapshots[i]['created_at']+' · '+snapshots[i].get('kind','decision'))
            ignored={'created_at','id'}
            diff=changes({k:v for k,v in prior.items() if k not in ignored},{k:v for k,v in snapshots[other].items() if k not in ignored})
            if diff:
                a,b=st.columns(2)
                for col,snapshot,label in [(a,prior,'Previous decision'),(b,snapshots[other],'Updated decision')]:
                    col.markdown('**'+label+'**')
                    allocation=snapshot.get('context',{}).get('allocation')
                    col.write('Conditional deployment: '+f'{sum(allocation["allocations"].values()):,.2f}' if allocation else 'No allocation computed in this snapshot')
                st.dataframe(pd.DataFrame([{'Changed input / output':item['path'],'Previous':json.dumps(item['before'],ensure_ascii=False,default=str)[:500],
                    'Updated':json.dumps(item['after'],ensure_ascii=False,default=str)[:500]} for item in diff]),hide_index=True,width='stretch')
                st.json(diff,expanded=False)
            else: st.info('No input or decision differences')


def scenario_widget_values(outcomes):
    s=outcomes['Base']['assumptions']
    return {'war_cash':s['cash'],'war_burn':s['monthly_burn'],'war_years':s['years'],
        'war_reduction':round(s['burn_reduction']*100),'war_implementation':s['implementation_cost'],
        'war_revenue':s['monthly_revenue'],'war_growth':s['monthly_revenue_growth']*100,
        'war_financing':s['financing'],'war_month':s['financing_month'],'war_ownership':s['ownership']*100,
        'war_dilution':s['dilution']*100,'war_invested':s['invested'],
        'war_downside':outcomes['Downside']['assumptions']['exit_value'],'war_base':s['exit_value'],
        'war_upside':outcomes['Upside']['assumptions']['exit_value']}


def fingerprint(mandate,deals,dossiers):
    import hashlib
    value={'mandate':mandate.model_dump(mode='json'),'deals':[d.model_dump(mode='json') for d in deals],
           'evidence':{cid:d.model_dump(mode='json') for cid,d in dossiers.items()}}
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def context_fingerprint(ctx):
    import hashlib
    return hashlib.sha256(json.dumps({k:v for k,v in ctx.items() if k!='created_at'},sort_keys=True,default=str).encode()).hexdigest()


def current_allocation(mandate,deals,dossiers):
    if st.session_state.get('allocation_context')==fingerprint(mandate,deals,dossiers): return st.session_state.get('allocation')
    if st.session_state.get('allocation'): st.info('Inputs or evidence changed. Recompute allocation in Portfolio Lab.')
    return None


def _is_number(value):
    import math
    try: return math.isfinite(float(value))
    except ValueError: return False


def _csv(value): return list(dict.fromkeys(x.strip() for x in value.split(',') if x.strip()))


def discovery_request(settings,store,filters,cursor=None,refresh=False):
    from dataclasses import replace
    api=Crustdata(replace(settings,refresh_data=refresh),store)
    try:
        with st.spinner('Querying Crustdata company index'):
            st.session_state['discovery_page']=search_companies(api,**filters,cursor=cursor)
            st.session_state['discovery_filters']=filters
            st.session_state.pop('discovery_error',None)
    except (ResearchError,ValueError,TypeError) as exc:
        st.session_state['discovery_error']=str(exc); st.error(str(exc))
    finally: api.close()


def identity_controls(settings,store):
    with st.expander('Resolve or disambiguate company identity'):
        st.caption('Exact domain first. Secondary name results are candidates until a domain/alias is validated or you explicitly confirm a canonical identity. No enrichment is performed here.')
        query=st.text_input('Identity domain or company name',key='identity_query')
        hint=st.text_input('Company name for secondary lookup (optional)',key='identity_hint')
        refresh=st.checkbox('Refresh identity lookup',key='identity_refresh')
        if st.button('Check identity',disabled=not query):
            from dataclasses import replace
            api=Crustdata(replace(settings,refresh_data=refresh),store)
            try:
                company,result,method=identify_company(api,query,name_hint=hint)
                st.session_state['identity_options']=candidate_rows(result)
                st.success(method+' · '+str((company.get('basic_info') or {}).get('name')))
                st.session_state['identity_options_query']=query
            except IdentityError as exc:
                st.session_state['identity_options']=exc.options
                st.session_state['identity_options_query']=query
                st.warning(str(exc))
            except (ResearchError,ValueError) as exc: st.error(str(exc))
            finally: api.close()
        options=st.session_state.get('identity_options',[])
        if options:
            st.dataframe(pd.DataFrame(options),hide_index=True,width='stretch')
            valid=[r for r in options if r.get('domain')]
            if valid:
                chosen=st.selectbox('Candidate to confirm',range(len(valid)),format_func=lambda i:f'{valid[i]["name"]} · {valid[i]["domain"]} · ID {valid[i]["company_id"]}')
                confirm=st.checkbox('I compared the candidate name and primary domain and confirm this identity')
                if st.button('Use confirmed company identity',disabled=not confirm):
                    from autopsy.ingestion import normalize
                    original=normalize(st.session_state['identity_options_query'])
                    selections=dict(st.session_state.get('identity_selections',{}))
                    selections[original]={'company_id':valid[chosen]['company_id'],'domain':valid[chosen]['domain']}
                    st.session_state['identity_selections']=selections
                    st.session_state['shortlist_text']=original
                    st.success('Identity selected. Launch investigation below; canonical ID and domain are checked again.')
