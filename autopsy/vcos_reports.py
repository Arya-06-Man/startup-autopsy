"""Portable committee artifacts; all HTML data is escaped."""
import json
from html import escape


def export(context,committee=None):
    for perspective in (committee or {}).get('perspectives',[]):
        for argument in perspective.get('thesis',[])+perspective.get('challenges',[]):
            if not argument.get('references') or not set(argument['references'])<=set(context['references']):
                raise ValueError('Unsupported committee reference in report')
    record={'product':'Startup Autopsy VCOS','context':context,'committee':committee,
            'limitations':['Company observations are not independently verified unless explicitly labeled.',
            'Financials and documents are user attestations; models are deterministic scenarios, not forecasts.',
            'Conditional allocations are subject to human diligence and approval; no investments executed.']}
    raw=json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)
    lines=['# Startup Autopsy VCOS','Autonomous Venture Capital Intelligence & Decision Platform',
           '## Investment mandate', '```json',json.dumps(context['mandate'],indent=2,ensure_ascii=False),'```']
    for d in context['deals']:
        lines+=['## '+escape(d['terms']['name']), '**'+d['readiness']['status']+'**',
                '### Valuation, supplied financials and modeled metrics','```json',json.dumps(d,indent=2,ensure_ascii=False,default=str),'```']
    lines+=['## War Room scenario outcomes','```json',json.dumps(context.get('war_room'),indent=2),'```',
            '## Conditional allocation','```json',json.dumps(context.get('allocation'),indent=2),'```',
            '## Investment committee arguments','```json',json.dumps(committee,indent=2,ensure_ascii=False),'```',
            '## Data provenance and source ledger','```json',json.dumps(context['references'],indent=2,ensure_ascii=False),'```',
            '## Limitations']+record['limitations']
    md='\n\n'.join(lines)
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
        body+=table(['Scenario','Exhaustion month','Financing received','Exit proceeds','MOIC','Annualized return'],[
            [name,value['cash_exhaustion_month'],value['financing_received'],value['exit_proceeds'],value['moic'],value['annualized_return']] for name,value in scenarios.items()])
        body+='<p>Absence of an exhaustion month means cash survives the modeled horizon. Assumptions appear in the audit appendix. These are scenarios, not validated forecasts.</p>'
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
    body+=table(['Evidence ID','Observation','Status','Provider observation','Publication','Retrieval','Source'],[
        [key,value['fact'],value['type'],value.get('observed'),value.get('published'),value.get('retrieved'),value.get('source')] for key,value in evidence]) if evidence else '<p>No external evidence supplied; more diligence required.</p>'
    body+='<h2>Limitations & next action</h2>'+bullets(record['limitations'])
    body+='<p>Resolve the listed approval conditions, reconcile conflicting observations and confirm primary financial and legal records. Recompute after changing terms, assumptions or evidence. No transaction or outreach has been executed.</p>'
    body+='<details><summary>Complete supplied inputs, calculations and source values</summary><pre>'+escape(raw)+'</pre></details>'
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Startup Autopsy VCOS · Investment committee</title><style>body{font:14px/1.6 system-ui;color:#243247;background:#f8fafc;max-width:1150px;margin:42px auto;padding:28px}header{border-bottom:3px solid #187e70;padding-bottom:24px}h1{font-size:32px;letter-spacing:-1px;margin:8px 0}h2{font-size:21px;margin-top:38px}h3{font-size:17px}h4{font-size:14px}.eyebrow{font-size:11px;letter-spacing:2px;color:#187e70}table{border-collapse:collapse;width:100%;background:white;font-size:12px;table-layout:auto}td,th{text-align:left;border-bottom:1px solid #dce3eb;padding:10px;overflow-wrap:anywhere;vertical-align:top}th{background:#eef2f6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:24px;border:1px solid #ddd}small{color:#64748b}details{margin-top:32px}@media print{body{margin:0;padding:12px;background:white}h2,h3{break-after:avoid}tr{break-inside:avoid}details{display:none}}</style>'''+body+'</html>'
    return {'json':raw,'md':md,'html':html}
