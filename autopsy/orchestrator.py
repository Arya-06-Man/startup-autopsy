from autopsy.models import Run,Dossier,now
from autopsy.api import ResearchError
from autopsy.research import gather,search_focus,fetch_lead
from autopsy.evidence import verify
from autopsy.risk import assess
from autopsy.identity import IdentityError


def actions(dossier,plan=None):
    signals=dossier.assessment.signals
    questions=['Can you share dated monthly headcount and open-role snapshots using consistent definitions?',
               'Which changes reflect planned efficiency, roles filled, or changes in data coverage?',
               'Can you provide the current leadership roster and dated explanations for any changes?',
               'Can you share current cash, positive monthly net burn, and their financial as-of date?']
    if plan: questions.extend(plan.questions)
    return {'urgency':'Within 48 hours' if dossier.assessment.label=='Urgent review' else 'Next portfolio review',
            'next_steps':['Validate provider observations with company-owned records.','Review fetched articles for attribution, dates and original reporting.','Reconcile discrepancies before investment decisions.'],
            'questions':questions,
            'hypotheses':[h.model_dump() for h in plan.hypotheses] if plan else [
                {'explanation':'Observed contraction may reflect an operating plan change; financial distress remains unestablished.',
                 'alternative':s.alternatives[0], 'evidence_ids':s.evidence_ids} for s in signals if s.severity>0],
            'email':f'Subject: Portfolio monitoring follow-up — {dossier.name or dossier.query}\n\nHi team,\n\nWe are refreshing our portfolio monitoring records and would appreciate your context on the following questions:\n\n'+'\n'.join('- '+q for q in questions)+'\n\nWe will reconcile third-party observations with your records before drawing conclusions.\n\nThank you.',
            'runway':'Runway cannot be estimated from available evidence.'}


def investigate(queries,api,store,planner=None,progress=None,identity_selections=None):
    if not queries: raise ValueError('Enter at least one company')
    run=Run(companies=[Dossier(query=q) for q in queries]); store.save(run)
    canonical=set()
    for d in run.companies:
        def stage(name,detail):
            d.trace.append({'stage':name,'at':now(),'detail':detail})
            run.usage=api.usage(); store.save(run)
            if progress: progress(d.query,name,detail)
        plan=None
        try:
            if identity_selections and d.query in identity_selections:
                d.metadata['identity_selection']=identity_selections[d.query]
            stage('PLAN','Resolve identity; require dated comparable counts and attributed sources. Permitted tools: identify, enrich, search, fetch.')
            d.status='running'
            stage('GATHER','Retrieve company, workforce, hiring, funding, leadership and news records.')
            gather(api,d,canonical)
            if d.company_id in canonical:
                d.status='duplicate'; d.errors.append('Canonical company already investigated in this run.'); continue
            canonical.add(d.company_id)
            d.evidence=verify(d.evidence); d.assessment=assess(d.evidence)
            stage('DETECT',f'{len(d.assessment.signals)} comparable trends; coverage {d.assessment.coverage:g}%.')
            stage('HYPOTHESIZE','Consider operating plan changes, roles filled and provider coverage changes.')
            if planner:
                plan=planner.plan(d)
                if planner.error:
                    d.trace.append({'stage':'LLM DIAGNOSTIC','at':now(),'detail':planner.error})
            d.metadata['analysis_engine']='GEMINI' if plan else 'DETERMINISTIC FALLBACK'
            d.metadata['llm_model']=planner.model if plan else None
            d.metadata['llm_diagnostic']=planner.error if planner else 'No planner configured'
            d.metadata['llm_diagnostics']=planner.diagnostics() if planner else {'provider':'NONE','status':'DETERMINISTIC FALLBACK'}
            focuses=[s.category for s in sorted(d.assessment.signals,key=lambda s:s.severity,reverse=True) if s.severity>0]
            focuses+=['leadership' if not any(e.category=='leadership_snapshot' for e in d.evidence) else 'business','business']
            if plan and plan.focus!='stop': focuses.insert(0,plan.focus)
            focuses=list(dict.fromkeys(focuses))
            if plan and plan.focus=='stop': focuses=[]
            for focus in focuses[:max(0,min(api.settings.max_iterations,4))]:
                stage('INVESTIGATE',f'Investigate {focus}: evidence-dependent search, then fetch up to two source documents.')
                try:
                    leads=search_focus(api,d,focus); fetch_lead(api,d,leads)
                except (ResearchError,ValueError) as exc:
                    d.errors.append(str(exc)); break
            stage('VERIFY','Preserve conflicting values; search snippets do not establish events; no automatic independent corroboration.')
            d.evidence=verify(d.evidence); d.assessment=assess(d.evidence)
            stage('ASSESS',d.assessment.label+'; missing evidence is not safety.')
            d.status='partial' if d.errors else 'complete'
        except (ResearchError,ValueError,TypeError,KeyError) as exc:
            if isinstance(exc,IdentityError): d.metadata['identity_candidates']=exc.options
            d.errors.append(str(exc)); d.status='partial' if d.evidence else 'failed'
            d.evidence=verify(d.evidence); d.assessment=assess(d.evidence)
        finally:
            d.advice=actions(d,plan)
            stage('DELIVER','Dossier and source ledger saved. Follow-up drafts are never sent.')
    run.status=('complete' if all(d.status in ('complete','duplicate') for d in run.companies) else
                'failed' if not any(d.evidence for d in run.companies) else 'partial')
    run.usage=api.usage()
    engines={d.metadata.get('analysis_engine') for d in run.companies if d.metadata.get('analysis_engine')}
    run.usage['analysis_engine']=('GEMINI + DETERMINISTIC CALCULATIONS' if engines=={'GEMINI'} else
        'MIXED GEMINI / DETERMINISTIC FALLBACK' if 'GEMINI' in engines else 'DETERMINISTIC FALLBACK')
    if planner: run.usage.update(llm_calls=planner.calls,llm_model=planner.model,llm_diagnostic=planner.error,llm_diagnostics=planner.diagnostics())
    run.usage['incomplete_reasons']=[{'query':d.query,'status':d.status,'reasons':d.errors} for d in run.companies if d.status not in ('complete','duplicate')]
    if api.cache_hits: run.mode='CACHED REAL DATA' if not api.calls else 'LIVE DATA + CACHED REAL DATA'
    if not any(d.evidence for d in run.companies): run.mode='NO USABLE EVIDENCE'
    store.save(run)
    return run
