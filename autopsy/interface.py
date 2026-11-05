"""Reusable presentation, search and navigation. Existing services own all research/math."""
import json
from dataclasses import replace
from html import escape
import pandas as pd
import plotly.express as px
import streamlit as st
from autopsy.api import Crustdata,ResearchError
from autopsy.identity import identify_company,IdentityError,candidate_rows
from autopsy.mandate import Workspace
from autopsy.finance import deal_metrics,readiness
from autopsy.health import company_health
from autopsy.risk import metric_date
from autopsy.evidence import safe_url

ROUTES=['Overview','Company Search','Discover','Evidence & Reports','Evaluate','Portfolio Lab','War Room',
        'Investment Committee','Reports','Investigation History','Investment Mandate','Company Overview']
LABELS={'Overview':'⌂  Overview','Company Search':'⌕  Company Search','Discover':'◇  Startup Discovery',
        'Evidence & Reports':'▤  Due Diligence','Evaluate':'⇄  Deal Comparison','Portfolio Lab':'▥  Portfolio Lab',
        'War Room':'◴  VC War Room','Investment Committee':'⚖  Investment Committee','Reports':'▣  Reports',
        'Investigation History':'↶  Investigation History','Investment Mandate':'≡  Investment Mandate','Company Overview':'◉  Company Overview'}
TITLES={k:v.split('  ',1)[-1] for k,v in LABELS.items()}
DESCRIPTIONS={'Overview':'Discover companies, investigate opportunities, compare deals and make evidence-backed investment decisions.',
 'Company Search':'Find a company by name or website. Confirm its identity before starting research.',
 'Discover':'Screen the company index against your criteria, then investigate a bounded shortlist.',
 'Evidence & Reports':'Investigate companies and follow the evidence behind every finding.',
 'Evaluate':'Compare operating evidence, valuation and supplied investment terms.',
 'Portfolio Lab':'Allocate capital within your mandate. Keeping capital uninvested is a valid decision.',
 'War Room':'Explore operating assumptions and financing outcomes. Scenarios are not verified forecasts.',
 'Investment Committee':'Challenge the thesis and prepare a sourced decision with explicit approval conditions.',
 'Reports':'Open, download and print your investment work products.',
 'Investigation History':'Reopen original dossiers, source dates and preserved execution results.',
 'Investment Mandate':'Define your capital, preferences and hard exposure constraints.',
 'Company Overview':'Company intelligence, operating evidence and the next diligence questions.'}


def styles():
    st.markdown('''<style>
    .block-container{max-width:1400px;padding:1.5rem 2.5rem 3rem}h1{font-size:1.9rem!important;font-weight:650!important;letter-spacing:-.035em;margin-bottom:.1rem}h2{font-size:1.35rem!important;letter-spacing:-.02em}h3{font-size:1.05rem!important}p{line-height:1.55}
    [data-testid="stSidebar"]{border-right:1px solid #263447;min-width:255px} [data-testid="stSidebar"] [data-testid="stRadio"] label{padding:3px 0;font-size:.95rem} [data-testid="stSidebar"] .block-container{padding-top:1rem}
    [data-testid="stMetric"]{background:#121c2a;border:1px solid #29374a;border-radius:10px;padding:14px} [data-testid="stMetricValue"]{font-size:1.5rem} [data-testid="stMetricLabel"]{color:#a9b6c9}
    [data-testid="stVerticalBlockBorderWrapper"]{border-radius:10px} .stButton>button,.stDownloadButton>button{border-radius:7px;font-weight:550} .stTabs [data-baseweb="tab-list"]{gap:18px} .eyebrow{font-size:.7rem;color:#90a6be;letter-spacing:.12em;text-transform:uppercase} .source-tag{display:inline-block;border:1px solid #33465e;color:#afc1d5;border-radius:5px;padding:3px 8px;margin:0 6px 6px 0;font-size:.72rem} .muted{color:#a1b1c6} a{color:#63bfae} [data-testid="stForm"]{border-color:#29374a}
    @media(max-width:750px){.block-container{padding:1.2rem 1rem}h1{font-size:1.6rem!important}[data-testid="stMetricValue"]{font-size:1.2rem}}
    </style>''',unsafe_allow_html=True)


def go(page,**state):
    st.session_state.update(state)
    st.session_state['requested_section']=page
    st.rerun()


def heading(title,description='',group='WORKSPACE'):
    st.markdown('<div class="eyebrow">'+escape(group)+'</div>',unsafe_allow_html=True)
    st.title(title)
    if description: st.caption(description)


def empty(title,description,action=None,target=None,key=None):
    with st.container(border=True):
        st.markdown('**'+title+'**')
        st.write(description)
        if action and st.button(action,key=key,type='primary'): go(target)


def source_tags(mode,retrieved=None,observed=None,timestamp_label='Retrieved'):
    values=[mode or 'Source mode unknown',timestamp_label+' '+str(retrieved or 'unknown')]
    if observed: values.append('Observed '+str(observed))
    st.markdown(''.join('<span class="source-tag">'+escape(str(v))+'</span>' for v in values),unsafe_allow_html=True)


def money(value,currency='INR'):
    return 'Unknown' if value is None else f'{currency} {value:,.0f}'


def catalog(store,workspace):
    result={}
    for record in reversed(workspace.list('companies')):
        if isinstance(record.get('company'),dict): result[record['company']['id']]=record['company']
    # Prefer the latest saved research for diligence state; original runs remain immutable.
    for run in reversed(store.runs()):
        for d in run.companies:
            if not d.company_id or d.status=='duplicate': continue
            current=result.get(d.company_id,{})
            counts=[e for e in d.evidence if e.category in ('workforce_snapshot','workforce') and isinstance(e.value,(int,float)) and e.status!='disputed/conflicting']
            counts.sort(key=lambda e:(e.category=='workforce_snapshot',metric_date(e) or e.retrieved_at))
            latest=counts[-1] if counts else None
            health=company_health(d)
            basic=d.metadata
            industries=basic.get('industries') or current.get('industry')
            result[d.company_id]={**current,'id':d.company_id,'name':d.name or d.query,'domain':d.domain or current.get('domain',''),
                'industry':', '.join(industries) if isinstance(industries,list) else industries,
                'geography':current.get('geography'),'headcount':latest.value if latest else current.get('headcount'),
                'observed':metric_date(latest) if latest else current.get('observed'),'retrieved_at':health['retrieved_at'] or current.get('retrieved_at'),
                'mode':run.mode,'run_id':run.id,'status':d.status,'dossier':d.model_dump(mode='json')}
    return result


def remember_company(workspace,company,result):
    basic=company.get('basic_info') or {}
    taxonomy=company.get('taxonomy') or {}
    industries=basic.get('industries') or taxonomy.get('professional_network_industry')
    item={'id':str(company['crustdata_company_id']),'name':basic.get('name') or basic.get('primary_domain') or 'Unnamed company',
        'domain':basic.get('primary_domain'),'industry':', '.join(industries) if isinstance(industries,list) else industries,
        'geography':(company.get('locations') or {}).get('country'),'headcount':(company.get('headcount') or {}).get('total'),
        'observed':None,'retrieved_at':result['retrieved_at'],'mode':result['mode'],'status':'discovered','raw':company}
    workspace.save('companies',{'id':item['id'],'company':item})
    return item


def add_compare(item,workspace):
    pool=dict(st.session_state.get('evaluation_pool',{}))
    if item['id'] not in pool and len(pool)>=5:
        st.error('A comparison can contain up to five companies. Remove one before adding another.'); return False
    pool[item['id']]={'name':item['name'],'domain':item.get('domain') or ''}
    st.session_state['evaluation_pool']=pool
    workspace.save('comparisons',{'id':'active','name':'Working comparison','pool':pool,'deals':st.session_state.get('vcos_deals',[])})
    return True


def company_actions(item,workspace,key):
    a,b,c,d=st.columns(4)
    if a.button('View Company',key=key+'_view',width='stretch'): go('Company Overview',selected_company_id=item['id'])
    if b.button('Investigate',key=key+'_investigate',disabled=not item.get('domain'),width='stretch'):
        go('Evidence & Reports',shortlist_text=item['domain'],selected_company_id=item['id'])
    if c.button('Add to Compare',key=key+'_compare',width='stretch'):
        if add_compare(item,workspace): go('Evaluate')
    if d.button('Add to Watchlist',key=key+'_watch',disabled=not item.get('domain'),width='stretch'):
        workspace.save('watchlists',{'name':item['name']+' watchlist','domains':[item['domain']],
            'source':item['mode'],'retrieved_at':item['retrieved_at']})
        st.success('Saved to a named local watchlist.')


def company_card(item,workspace,key,actions=True):
    with st.container(border=True):
        a,b=st.columns([3,2])
        a.markdown('**'+str(item['name'])+'**')
        a.caption(item.get('domain') or 'Primary domain unknown')
        b.caption('Diligence: '+str(item.get('status','discovered')).replace('complete','completed'))
        st.caption(' · '.join(str(v) for v in [item.get('industry') or 'Industry unknown',item.get('geography') or 'Geography unknown',
            ('Employees: '+str(item['headcount'])) if item.get('headcount') is not None else 'Employee count unknown']))
        source_tags(item.get('mode'),item.get('retrieved_at'),item.get('observed'))
        if actions: company_actions(item,workspace,key)


def global_search(settings,store,workspace):
    with st.form('global_company_lookup'):
        a,b=st.columns([5,1],vertical_alignment='bottom')
        query=a.text_input('Search companies',value=st.session_state.get('company_search_query',''),
            placeholder='Search startups by company name or website...',help='For example Razorpay, Zepto, retool.com or notion.so. Lookup runs only on submission.')
        submit=b.form_submit_button('Search',type='primary',width='stretch',disabled=not settings.api_key)
        refresh=st.checkbox('Refresh lookup',value=False,help='Bypass local cache for this lookup; underlying provider observations may still be older.')
    if not settings.api_key: st.caption('Configure CRUSTDATA_API_KEY in Settings / Status to search. Saved research remains accessible.')
    if submit:
        st.session_state['company_search_query']=query.strip()
        st.session_state.pop('lookup_candidates',None)
        st.session_state.pop('lookup_company',None)
        st.session_state.pop('lookup_error',None)
        if not query.strip(): st.session_state['lookup_error']='Enter a company name or website.'
        else:
            api=Crustdata(replace(settings,refresh_data=refresh),store)
            try:
                with st.spinner('Looking up company identity in Crustdata'):
                    company,result,method=identify_company(api,query)
                    item=remember_company(workspace,company,result)
                    st.session_state['lookup_company']=item
            except IdentityError as exc:
                st.session_state['lookup_candidates']=exc.options
                st.session_state['lookup_error']='No unique validated identity. Compare the provider candidates below; nothing has been selected.' if exc.options else 'No validated company found. Try its primary website or exact company name.'
            except (ResearchError,ValueError,TypeError) as exc: st.session_state['lookup_error']=str(exc)
            finally: api.close()
    if st.session_state.get('lookup_error'): st.warning(st.session_state['lookup_error'])
    options=st.session_state.get('lookup_candidates',[])
    if options:
        st.dataframe(pd.DataFrame([{'Company':r['name'],'Domain':r['domain'] or 'Unknown','Provider match':r.get('confidence'),
            'Retrieved':r['retrieved_at']} for r in options]),hide_index=True,width='stretch')
        valid=[r for r in options if r.get('domain')]
        if valid:
            selected=st.selectbox('Candidate identity',range(len(valid)),format_func=lambda i:f'{valid[i]["name"]} · {valid[i]["domain"]}')
            confirm=st.checkbox('I confirm this company name and domain')
            if st.button('Confirm company',disabled=not confirm,type='primary'):
                api=Crustdata(settings,store)
                try:
                    with st.spinner('Revalidating canonical ID and domain'):
                        company,result,_=identify_company(api,st.session_state['company_search_query'],selection=valid[selected])
                        st.session_state['lookup_company']=remember_company(workspace,company,result)
                        st.session_state.pop('lookup_candidates',None); st.session_state.pop('lookup_error',None)
                        st.rerun()
                except (ResearchError,ValueError) as exc: st.error(str(exc))
                finally: api.close()
    item=st.session_state.get('lookup_company')
    if item:
        latest=catalog(store,workspace).get(item['id'],item)
        company_card(latest,workspace,'global_result')


def onboarding(workspace,mandate,deals,runs):
    prefs=next((r for r in workspace.list('preferences') if r.get('id')=='interface'),{})
    if prefs.get('onboarding_skipped'): return
    stages=[('Mandate',bool(mandate)),('Search / upload',bool(runs or st.session_state.get('lookup_company') or st.session_state.get('evaluation_pool'))),
            ('Investigate & compare',len(deals)>=2),('Scenarios & allocation',bool(st.session_state.get('war_outcomes') or st.session_state.get('allocation'))),
            ('Committee report',bool(workspace.list('reports')))]
    with st.container(border=True):
        a,b=st.columns([5,1])
        a.markdown('**Your first investment workflow**')
        a.caption(' → '.join(('✓ ' if done else str(i+1)+'. ')+label for i,(label,done) in enumerate(stages)))
        if b.button('Skip guide',width='stretch'):
            workspace.save('preferences',{'id':'interface','onboarding_skipped':True}); st.rerun()
        if not mandate and st.button('Create Investment Mandate',type='primary'): go('Investment Mandate')


def overview(settings,store,workspace,mandate,deals,runs,dossiers):
    heading('Investment Intelligence',DESCRIPTIONS['Overview'],'HOME')
    global_search(settings,store,workspace)
    st.markdown('#### Start your next decision')
    actions=[('◇','Discover Startups','Find investment opportunities matching your criteria.','Discover'),
        ('⇄','Compare Deals','Evaluate companies, valuations and investment terms side by side.','Evaluate'),
        ('▥','Portfolio Lab','Plan capital allocations and manage concentration.','Portfolio Lab'),
        ('◴','VC War Room','Stress-test runway, funding and exit scenarios.','War Room')]
    for col,(icon,title,description,target) in zip(st.columns(4),actions):
        with col.container(border=True):
            st.markdown('**'+icon+'  '+title+'**'); st.caption(description)
            if st.button('Open '+title,key='quick_'+target,width='stretch'): go(target)
    onboarding(workspace,mandate,deals,runs)
    if mandate:
        a,b,c,d=st.columns(4)
        a.metric('Investment budget',money(mandate.capital,mandate.currency))
        b.metric('Available after reserves',money(mandate.deployable,mandate.currency))
        c.metric('Follow-on reserve',money(mandate.reserve,mandate.currency))
        d.metric('Deals in comparison',len(deals) or len(st.session_state.get('evaluation_pool',{})))
        st.caption(f'{mandate.name} · {mandate.risk} · {mandate.horizon_years} years · Max company exposure {mandate.company_limit:.0%}')
        if st.button('Review investment mandate'): go('Investment Mandate')
    a,b=st.columns(2)
    with a:
        st.markdown('#### Recent investigations')
        if runs:
            st.dataframe(pd.DataFrame([{'Companies':', '.join(d.name or d.query for d in r.companies),'Status':r.status,'Date':r.created_at[:16],
                'Source mode':r.mode} for r in runs[:4]]),hide_index=True,width='stretch')
            if st.button('Open investigation history'): go('Investigation History')
        else: st.caption('Search above to investigate your first company, or upload a portfolio in Due Diligence.')
        comparisons=workspace.list('comparisons')
        if comparisons:
            st.markdown('#### Saved comparisons')
            for comparison in comparisons[:3]:
                st.write(comparison.get('name','Comparison')+' · '+str(len(comparison.get('deals') or comparison.get('pool',{})))+' opportunities')
            if st.button('Reopen deal comparison'): go('Evaluate')
    with b:
        if mandate and deals:
            st.markdown('#### Decisions requiring attention')
            for deal in deals:
                result=readiness(mandate,deal,dossiers.get(deal.company_id))
                st.write('**'+deal.name+'** · '+result['status'].title())
                if result['violations']: st.warning('; '.join(result['violations']))
                elif result['missing']: st.caption('Next: '+', '.join(result['missing'][:2]))
        reports=workspace.list('reports')
        if reports:
            st.markdown('#### Recent reports')
            for record in reports[:3]: st.write(record.get('title','Committee memo')+' · '+record['created_at'][:16])
            if st.button('Open reports'): go('Reports')
        if not (mandate and deals) and not reports:
            st.markdown('#### What happens next?')
            st.write('Confirm a company, investigate its evidence, then supply terms to compare investment opportunities.')
            if st.button('Search a company'): go('Company Search')


def company_overview(store,workspace,mandate,deals):
    items=catalog(store,workspace)
    if not items:
        empty('No company selected','Search a company to open its intelligence dossier.','Search Companies','Company Search'); return
    cid=st.session_state.get('selected_company_id')
    if cid not in items: cid=next(iter(items))
    cid=st.selectbox('Company context',list(items),index=list(items).index(cid),format_func=lambda value:items[value]['name'])
    st.session_state['selected_company_id']=cid
    item=items[cid]
    heading(item['name'],item.get('domain') or 'Primary domain unavailable','RESEARCH / COMPANY OVERVIEW')
    st.caption(' · '.join(str(v) for v in [item.get('industry') or 'Sector unknown',item.get('geography') or 'Location unknown']))
    source_tags(item.get('mode'),item.get('retrieved_at'),item.get('observed'))
    company_actions(item,workspace,'company_header')
    raw=item.get('dossier')
    if not raw:
        empty('Identity discovered; diligence not yet completed','Only identity/index observations are available. Investigate to retrieve operating evidence and its source history.')
        return
    from autopsy.models import Dossier
    d=Dossier.model_validate(raw); health=company_health(d)
    st.subheader('Executive summary')
    st.write(d.metadata.get('description') or 'A verified business-model description has not been supplied.')
    st.caption(health['verification']+' · '+health['execution']+' execution · '+f'{d.assessment.coverage:g}% scored trend coverage')
    a,b,c=st.columns(3)
    a.metric('Employees',str(item['headcount']) if item.get('headcount') is not None else 'Unknown')
    hiring=[e for e in d.evidence if e.category in ('hiring_snapshot','hiring') and isinstance(e.value,(int,float)) and e.status!='disputed/conflicting']
    hiring.sort(key=lambda e:(e.category=='hiring_snapshot',metric_date(e) or e.retrieved_at))
    b.metric('Open roles',str(hiring[-1].value) if hiring else 'Unknown')
    c.metric('Evidence observations',len(d.evidence))
    for col,category,label in [(a,'workforce','Employees'),(b,'hiring','Open roles')]:
        observations=[{'Date':metric_date(e),label:e.value} for e in d.evidence if e.category==category and isinstance(e.value,(int,float)) and metric_date(e) and e.status!='disputed/conflicting']
        if len(observations)>1:
            col.plotly_chart(px.line(pd.DataFrame(observations).sort_values('Date'),x='Date',y=label,color_discrete_sequence=['#63bfae']),width='stretch')
        else: col.caption(label+': comparable dated history unavailable.')
    for signal in d.assessment.signals:
        st.write('**'+signal.category.title()+'** · '+signal.explanation)
        with st.expander('Source details · '+signal.category):
            st.dataframe(pd.DataFrame([{'Evidence':e.id,'Observation date':metric_date(e),'Value':e.value,'Source':e.source,'Retrieved':e.retrieved_at} for e in d.evidence if e.id in signal.evidence_ids]),hide_index=True,width='stretch')
            st.caption('Other explanations: '+'; '.join(signal.alternatives))
    for title,categories in [('Leadership developments',('leadership_snapshot',)),('Funding observations',('funding','funding_snapshot')),('Business source leads',('news_observation','business_raw'))]:
        with st.expander(title):
            observations=[e for e in d.evidence if e.category in categories]
            if not observations: st.caption('No supported observations available.')
            for e in observations[:8]:
                st.write(e.fact); st.caption(f'{e.status} · event {e.event_date or "unknown"} · published {e.publication_date or "unknown"}')
                st.json(e.value,expanded=False)
                if safe_url(e.source): st.link_button('Source '+e.id,e.source)
            if len(observations)>8: st.caption('Full records remain available in Due Diligence and the source ledger.')
    financial=next((deal for deal in deals if deal.company_id==cid),None)
    st.subheader('Financial fundamentals')
    if financial:
        metrics=deal_metrics(financial)
        st.caption(financial.provenance+' · financial as-of '+str(financial.financial_date or 'unknown'))
        st.dataframe(pd.DataFrame([{'Revenue':financial.revenue,'Monthly net burn':financial.monthly_burn,'Cash':financial.cash,'Runway months':metrics['runway_months']}]),hide_index=True,width='stretch')
    else: st.caption('Company financial statements have not been supplied. Cash, revenue and runway remain unknown.')
    st.subheader('Unresolved diligence')
    for issue in d.errors+d.assessment.missing: st.write('• '+issue)
    if st.button('Open full evidence & investigation history'): go('Evidence & Reports',requested_run_id=item['run_id'])


def comparison_cards(mandate,deals,dossiers):
    if not deals: return
    for offset in range(0,len(deals),3):
        batch=deals[offset:offset+3]
        for col,deal in zip(st.columns(min(3,len(batch))),batch):
            with col.container(border=True):
                st.markdown('### '+deal.name)
                d=dossiers.get(deal.company_id); metrics=deal_metrics(deal); result=readiness(mandate,deal,d)
                st.caption((d.domain if d else deal.company_id)+' · '+result['status'].title())
                st.metric('Proposed investment',money(deal.investment,deal.currency))
                st.metric('Implied ownership',f'{metrics["ownership"]:.2%}' if metrics['ownership'] is not None else 'Unsupported terms')
                st.caption('Post-money: '+money(metrics['post_money'],deal.currency))
                st.caption('Revenue: '+money(deal.revenue,deal.currency)+' · Runway: '+(f'{metrics["runway_months"]:.1f} months' if metrics['runway_months'] is not None else 'Unknown'))
                st.caption(deal.provenance)
                if d:
                    h=company_health(d); st.caption(h['verification']+' · retrieved '+str(h['retrieved_at'] or 'unknown')[:19])
                    for s in d.assessment.signals: st.write(s.category.title()+': '+s.explanation)
                else: st.caption('No investigated evidence linked.')
                if result['violations']: st.error('; '.join(result['violations']))
                if result['missing']: st.caption('Missing: '+', '.join(result['missing'][:4]))
    st.caption('Comparisons reflect supplied terms and source coverage. Workforce growth alone does not determine investment suitability.')


def history_page(store):
    runs=store.runs()
    heading('Investigation History',DESCRIPTIONS['Investigation History'],'DOCUMENTS')
    if not runs:
        empty('No investigation history yet','Search or upload companies to create your first sourced investigation.','Search Companies','Company Search'); return
    for r in runs[:20]:
        with st.container(border=True):
            a,b=st.columns([4,1])
            a.markdown('**'+', '.join(d.name or d.query for d in r.companies)+'**')
            a.caption(r.created_at+' · '+r.status.upper()+' · '+r.mode)
            if b.button('Open investigation',key='history_'+r.id,width='stretch'): go('Evidence & Reports',requested_run_id=r.id)
