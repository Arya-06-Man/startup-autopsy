"""Portable committee artifacts; all HTML data is escaped."""
import json
from html import escape
import math
from autopsy.finance import Deal,deal_metrics
from autopsy.mandate import Mandate,category_key
from autopsy.models import Dossier
from autopsy.evidence import safe_url,validate_refs


def validate(context,committee=None):
    mandate=Mandate.model_validate(context['mandate'])
    deals=[Deal.model_validate(d['terms']) for d in context['deals']]
    if len({category_key(d.company_id) for d in deals})!=len(deals): raise ValueError('Duplicate report identities')
    ledger={}
    for cid,raw_dossier in context.get('dossiers',{}).items():
        dossier=Dossier.model_validate(raw_dossier)
        if dossier.company_id!=cid: raise ValueError('Report dossier identity mismatch')
        for e in dossier.evidence:
            if e.company_id!=cid: raise ValueError('Evidence assigned to another company')
            ledger[e.id]=e
        for signal in dossier.assessment.signals: validate_refs(signal.evidence_ids,dossier.evidence)
        for h in dossier.advice.get('hypotheses',[]): validate_refs(h['evidence_ids'],dossier.evidence)
    for d,record in zip(deals,context['deals']):
        if record['metrics']!=deal_metrics(d): raise ValueError('Stale financial calculations; regenerate the decision context')
        ref=context['references'].get('A-'+d.company_id)
        if not ref or ref.get('value')!=d.model_dump(mode='json'): raise ValueError('Terms reference does not match supplied deal inputs')
    for ref_id,ref in context['references'].items():
        if ref_id.startswith('A-'): continue
        e=ledger.get(ref_id)
        if not e or (ref.get('fact'),ref.get('source'),ref.get('company_id'))!=(e.fact,e.source,e.company_id):
            raise ValueError('Source reference does not resolve to the original company ledger')
    allocation=context.get('allocation')
    if allocation:
        amounts=allocation.get('allocations',{})
        if set(amounts)!={d.company_id for d in deals}: raise ValueError('Allocation company identities do not match the memo')
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in amounts.values()): raise ValueError('Invalid conditional allocation')
        if abs(allocation['reserve']-mandate.reserve)>.01 or abs(sum(amounts.values())+allocation['uninvested']-mandate.deployable)>.01:
            raise ValueError('Allocation does not reconcile to available capital and reserves')
        for field,limit in [('company_id',mandate.company_limit),('sector',mandate.sector_limit),('stage',mandate.stage_limit)]:
            categories={category_key(getattr(d,field)) for d in deals}|{category_key(getattr(h,field)) for h in mandate.existing}
            for value in categories:
                existing=sum(h.amount for h in mandate.existing if category_key(getattr(h,field))==value)
                new=sum(amounts[d.company_id] for d in deals if category_key(getattr(d,field))==value)
                if new>0 and existing+new>mandate.capital*limit+.01: raise ValueError('Conditional allocation violates '+field+' exposure')
        for d in deals:
            amount=amounts[d.company_id]
            if amount>0 and (amount<mandate.min_cheque-.01 or amount>min(mandate.max_cheque,d.investment)+.01):
                raise ValueError('Conditional allocation violates cheque limits')
    for perspective in (committee or {}).get('perspectives',[]):
        for argument in perspective.get('thesis',[])+perspective.get('challenges',[]):
            if not argument.get('references') or not set(argument['references'])<=set(context['references']):
                raise ValueError('Unsupported committee reference in report')


def export(context,committee=None):
    validate(context,committee)
    record={'product':'Startup Autopsy VCOS','context':context,'committee':committee,
            'limitations':['Company observations are not independently verified unless explicitly labeled.',
            'Financials and documents are user attestations; models are deterministic scenarios, not forecasts.',
            'Conditional allocations are subject to human diligence and approval; no investments executed.']}
    raw=json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)
    def fmt(value):
        if value is None: return 'Unknown'
        if isinstance(value,float): return f'{value:,.4f}'.rstrip('0').rstrip('.')
        if isinstance(value,(dict,list)): return json.dumps(value,ensure_ascii=False)
        return str(value)
    def cell(value): return escape(fmt(value))
    def table(headers,items):
        return '<table><thead><tr>'+''.join('<th>'+cell(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+cell(v)+'</td>' for v in row)+'</tr>' for row in items)+'</tbody></table>'
    def bullets(items): return '<ul>'+''.join('<li>'+cell(v)+'</li>' for v in items)+'</ul>'
    m=context['mandate']
    body='<header><p class="eyebrow">CONTEXTCON 04 · IIT KANPUR · INVESTING</p><h1>Startup Autopsy VCOS</h1><p>Investment committee · conditional decision memo</p><small>'+cell(context['created_at'])+' · '+cell(m['currency'])+' · '+cell(m['name'])+'</small></header>'
    allocation=context.get('allocation')
    total=sum(allocation['allocations'].values()) if allocation else None
    body+='<h2>Executive investment summary</h2><p>'+('No allocation has been computed; complete diligence and evaluate constraints.' if total is None else 'Conditional deployment: '+cell(m['currency'])+' '+cell(total)+'. '+('Current inputs support no new investment.' if total==0 else 'Human verification and approval are required before deployment.'))+'</p>'
    if context.get('validation_disclosure'): body+='<p>'+cell(context['validation_disclosure'])+'</p>'
    body+='<p>Company financial inputs are '+cell(', '.join(sorted({d['terms']['provenance'] for d in context['deals']})))+'. AI arguments below are hypotheses, not verified findings.</p>'
    body+='<h2>Decision readiness</h2>'+table(['Opportunity','Readiness','Approval conditions'],[
        [d['terms']['name'],d['readiness']['status'],'; '.join(d['readiness']['violations']+d['readiness']['missing']) or 'Human verification and committee approval required'] for d in context['deals']])
    body+='<h2>Investor mandate</h2>'+table(['Constraint','Reviewed value'],[
        ['Total capital at cost',m['capital']],['Currency',m['currency']],['Risk / horizon',m['risk']+' / '+str(m['horizon_years'])+' years'],
        ['Sectors / stages / geographies',[m['sectors'],m['stages'],m['geographies']]],['Cheque minimum / maximum',[m['min_cheque'],m['max_cheque']]],
        ['Company / sector / stage limits',[m['company_limit'],m['sector_limit'],m['stage_limit']]],
        ['Follow-on reserve',m['capital']*m['reserve_fraction']],['Liquidity buffer',m['liquidity_buffer']],['Existing holdings',m['existing']],['Hard rejection criteria',m['rejection_criteria']]])
    body+='<h2>Deal comparison & financial analysis</h2><p>Financial inputs are user-supplied and unverified. Blank source values remain unknown. Ordinary-equity ownership only.</p>'+table(
        ['Company','Proposed cheque','Post-money','Ownership fraction','Post-money / annual revenue','Runway months','Gross / operating margin'],[
        [d['terms']['name'],d['terms']['investment'],d['metrics']['post_money'],d['metrics']['ownership'],d['metrics']['valuation_revenue_multiple'],d['metrics']['runway_months'],[d['metrics']['gross_margin'],d['metrics']['operating_margin']]] for d in context['deals']])
    for d in context['deals']:
        body+='<h3>'+cell(d['terms']['name'])+'</h3><p>Supplied financial as-of: '+cell(d['terms']['financial_date'])+' · Terms reference: '+cell('A-'+d['terms']['company_id'])+'</p>'
        body+=bullets(d['metrics']['assumptions']+d['readiness'].get('coverage_warnings',[]))
    allocation=context.get('allocation')
    body+='<h2>Conditional capital allocation</h2>'
    if allocation:
        body+='<p>'+cell(allocation['reason'])+'</p>'+table(['Company ID','Conditional allocation'],list(allocation['allocations'].items()))
        body+=table(['Capital bucket','Amount'],[['Uninvested deployment capital',allocation['uninvested']],['Follow-on reserve',allocation['reserve']]])
        body+='<p>'+cell(allocation['assumptions'])+'</p>'
    else: body+='<p>No current allocation computed. No investment recommendation is implied.</p>'
    body+='<h2>War Room scenario outcomes</h2>'
    scenarios=context.get('war_room')
    if scenarios:
        body+='<p>'+cell(context.get('war_room_scope','User-modeled financial assumptions; not externally verified company forecasts.'))+'</p>'
        body+=table(['Scenario','Exhaustion month','Financing received','Exit proceeds','MOIC','Annualized return'],[
            [name,value['cash_exhaustion_month'],value['financing_received'],value['exit_proceeds'],value['moic'],value['annualized_return']] for name,value in scenarios.items()])
        body+='<p>Absence of an exhaustion month means cash survives the modeled horizon. Assumptions appear in the audit appendix. These are scenarios, not validated forecasts.</p>'
        if scenarios.get('Base'):
            body+='<h3>Supplied base-scenario assumptions</h3>'+table(['Input','Modeled value'],list(scenarios['Base']['assumptions'].items()))
    else: body+='<p>No War Room scenario supplied.</p>'
    body+='<h2>Investment committee challenge</h2>'
    if committee:
        body+='<p>'+cell(committee['engine'])+' · '+cell(committee['disclosure'])+'</p>'
        for perspective in committee['perspectives']:
            body+='<h3>'+cell(perspective['role'])+'</h3><small>'+cell(perspective['engine'])+'</small>'
            for label,key in [('Thesis','thesis'),('Counterarguments / conditions','challenges')]:
                body+='<h4>'+label+'</h4>'+bullets([a['claim']+' ['+', '.join(a['references'])+']' for a in perspective[key]])
            body+='<h4>Next diligence questions</h4>'+bullets(perspective['questions'])
        body+=bullets(committee.get('diagnostics',[]))
    else: body+='<p>Committee challenge has not been run. Readiness above remains deterministic.</p>'
    body+='<h2>Evidence provenance & operating observations</h2><p>Single-source observations are not independent verification. Source dates are preserved separately.</p>'
    evidence=[(key,value) for key,value in context['references'].items() if not key.startswith('A-')]
    relevant=set()
    for dossier in context.get('dossiers',{}).values():
        for signal in dossier.get('assessment',{}).get('signals',[]): relevant.update(signal['evidence_ids'])
    for perspective in (committee or {}).get('perspectives',[]):
        for argument in perspective['thesis']+perspective['challenges']: relevant.update(argument['references'])
    cited_evidence=[item for item in evidence if item[0] in relevant] or evidence[:10]
    body+=table(['Evidence ID','Observation','Status','Observation date','Event date','Publication','Provider update','Retrieval'],[
        [key,value['fact'],value['type'],value.get('observed'),value.get('event'),value.get('published'),value.get('provider_updated'),value.get('retrieved')] for key,value in cited_evidence]) if evidence else '<p>No external evidence supplied; more diligence required.</p>'
    body+='<p>'+str(len(evidence))+' original evidence records retained. Main table shows cited/core observations; the complete source values remain in the expandable audit appendix and JSON export.</p>'
    body+='<details><summary>Source links and retrieval modes</summary><ul>'+''.join('<li>'+cell(key)+' · '+('<a href="'+escape(value.get('source',''),quote=True)+'" rel="noopener noreferrer">'+cell(value.get('source'))+'</a>' if safe_url(value.get('source','')) else cell(value.get('source')))+' · '+cell(value.get('data_mode','Unknown / legacy record'))+'</li>' for key,value in evidence)+'</ul></details>'
    body+='<h2>Limitations & next action</h2>'+bullets(record['limitations'])
    body+='<p>Resolve the listed approval conditions, reconcile conflicting observations and confirm primary financial and legal records. Recompute after changing terms, assumptions or evidence. No transaction or outreach has been executed.</p>'
    body+='<details><summary>Complete supplied inputs, calculations and source values</summary><pre>'+escape(raw)+'</pre></details>'
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Startup Autopsy VCOS · Investment committee</title><style>body{font:14px/1.6 system-ui;color:#243247;background:#f8fafc;max-width:1150px;margin:42px auto;padding:28px}header{border-bottom:3px solid #187e70;padding-bottom:24px}h1{font-size:32px;letter-spacing:-1px;margin:8px 0}h2{font-size:21px;margin-top:38px}h3{font-size:17px}h4{font-size:14px}.eyebrow{font-size:11px;letter-spacing:2px;color:#187e70}table{border-collapse:collapse;width:100%;background:white;font-size:12px;table-layout:auto}td,th{text-align:left;border-bottom:1px solid #dce3eb;padding:10px;overflow-wrap:anywhere;vertical-align:top}th{background:#eef2f6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:24px;border:1px solid #ddd}small{color:#64748b}details{margin-top:32px}@media print{body{margin:0;padding:12px;background:white}h2,h3{break-after:avoid}tr{break-inside:avoid}details{display:none}}</style>'''+body+'</html>'
    def md_cell(value):
        return cell(value).replace('|','\\|').replace('\n',' ').replace('[','\\[').replace(']','\\]').replace('`','\\`')
    readable=['# Startup Autopsy VCOS','## Executive investment summary',
        'No allocation computed.' if total is None else f'Conditional deployment: {m["currency"]} {total:,.2f}. Human verification and approval required.',
        '## Side-by-side comparison',
        '| Company | Readiness | Proposed cheque | Post-money | Ownership | Runway months |',
        '|---|---|---:|---:|---:|---:|']
    for d in context['deals']:
        readable.append('| '+' | '.join(md_cell(v) for v in [d['terms']['name'],d['readiness']['status'],d['terms']['investment'],d['metrics']['post_money'],d['metrics']['ownership'],d['metrics']['runway_months']])+' |')
    readable+=['## Main concerns and next diligence actions']
    for d in context['deals']:
        readable+=['### '+md_cell(d['terms']['name'])]+['- '+md_cell(v) for v in d['readiness']['violations']+d['readiness']['missing']+d['readiness'].get('coverage_warnings',[])]
    readable+=['## Reviewed investment mandate',
        f'Capital: {m["currency"]} {m["capital"]:,.2f} · Risk: {md_cell(m["risk"])} · Horizon: {m["horizon_years"]} years.',
        f'Company / sector / stage limits: {m["company_limit"]:.0%} / {m["sector_limit"]:.0%} / {m["stage_limit"]:.0%}. Follow-on reserve: {m["reserve_fraction"]:.0%}.',
        '## Fundamental and operating analysis']
    for d in context['deals']:
        readable+=['### '+md_cell(d['terms']['name']),md_cell(d['terms']['provenance'])+'; financial as-of: '+md_cell(d['terms']['financial_date']),
            'Post-money / annual revenue: '+md_cell(d['metrics']['valuation_revenue_multiple'])+'; gross margin: '+md_cell(d['metrics']['gross_margin'])+'; operating margin: '+md_cell(d['metrics']['operating_margin'])]
        for signal in context.get('dossiers',{}).get(d['terms']['company_id'],{}).get('assessment',{}).get('signals',[]):
            readable.append('- '+md_cell(signal['explanation'])+' ['+', '.join(signal['evidence_ids'])+']')
    readable+=['## Portfolio diversification and conditional allocation']
    if allocation:
        readable += [md_cell(allocation['reason']),
            'Allocations: '+md_cell(allocation['allocations']),
            'Sector exposure: '+md_cell(allocation.get('sector_exposure',{})),
            'Stage exposure: '+md_cell(allocation.get('stage_exposure',{})),
            'Uninvested deployment capital: '+md_cell(allocation['uninvested'])+'; reserve: '+md_cell(allocation['reserve'])]
    else: readable+=['No current allocation computed.']
    readable+=['## Downside, base, upside and capital-loss scenarios',
        md_cell(context.get('war_room_scope','User-modeled assumptions, not validated forecasts.'))]
    if scenarios:
        readable+=['| Scenario | Exhaustion month | Proceeds | MOIC | Annualized return |','|---|---:|---:|---:|---:|']
        readable+=['| '+' | '.join(md_cell(v) for v in [name,out['cash_exhaustion_month'],out['exit_proceeds'],out['moic'],out['annualized_return']])+' |' for name,out in scenarios.items()]
    else: readable+=['No War Room scenario supplied.']
    readable+=['## Investment committee arguments — hypotheses, not verified facts']
    if committee:
        readable += [md_cell(committee['engine']),md_cell(committee['disclosure'])]
        for perspective in committee['perspectives']:
            readable+=['### '+md_cell(perspective['role'])+' · '+md_cell(perspective['engine'])]
            readable+=['- '+md_cell(a['claim'])+' ['+', '.join(a['references'])+']' for a in perspective['thesis']+perspective['challenges']]
            readable+=['- Diligence question: '+md_cell(q) for q in perspective['questions']]
    else: readable+=['Committee challenge not run.']
    readable+=['## Sources, dates, assumptions and limitations']
    for key,value in cited_evidence:
        readable+=['- '+md_cell(key)+' · '+md_cell(value['fact'])+' · '+md_cell(value['type'])+
            ' · observation: '+md_cell(value.get('observed'))+' · event: '+md_cell(value.get('event'))+
            ' · published: '+md_cell(value.get('published'))+' · provider update: '+md_cell(value.get('provider_updated'))+
            ' · retrieved: '+md_cell(value.get('retrieved'))+' · source: '+md_cell(value.get('source'))]
    readable+=record['limitations']
    readable+=['<details><summary>Complete supplied inputs, calculations, scenarios and evidence audit JSON</summary>',
        '```json\n'+raw+'\n```','</details>']
    return {'json':raw,'md':'\n\n'.join(readable),'html':html}
