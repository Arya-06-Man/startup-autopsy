import json
from jinja2 import Environment, select_autoescape
from autopsy.evidence import validate_refs

DISCLAIMER='Investigation priorities are heuristic monitoring aids, not probabilities of failure. Missing evidence is not evidence of safety. Hiring changes and funding silence do not establish financial distress.'


def validate(run):
    for d in run.companies:
        for signal in d.assessment.signals: validate_refs(signal.evidence_ids,d.evidence)
        for h in d.advice.get('hypotheses',[]): validate_refs(h['evidence_ids'],d.evidence)


def ledger(run):
    validate(run)
    return run.model_dump_json(indent=2)


def markdown(run):
    validate(run)
    lines=['# STARTUP AUTOPSY','Autonomous VC Portfolio Intelligence & Intervention Agent',f'Investigation: {run.id} | {run.created_at} | {run.mode}',DISCLAIMER,
           'Weights: workforce 35%, leadership 30%, hiring 20%, business 15%. Minimum 50% weighted coverage and two comparable categories; score normalized over observed categories. Leadership and article events remain unscored pending dated structured verification.',
           '## API usage',json.dumps(run.usage,ensure_ascii=False)]
    for d in sorted(run.companies,key=lambda d:d.assessment.score if d.assessment.score is not None else -1,reverse=True):
        a=d.assessment
        lines += [f'## {d.name or d.query}',f'Domain: {d.domain} | Canonical ID: {d.company_id} | Status: {d.status}',f'Priority: {a.score if a.score is not None else "Unscored"} | {a.label} | Coverage: {a.coverage}%', '### Observed trends']
        for s in a.signals:
            lines += [f'- {s.category}: {s.explanation} [{", ".join(s.evidence_ids)}]',f'  Alternative explanations: {"; ".join(s.alternatives)}']
        lines += ['### Missing evidence'] + ['- '+m for m in a.missing]
        lines += ['### Hypotheses — not established facts']
        for h in d.advice.get('hypotheses',[]): lines += [f'- {h["explanation"]} Alternative: {h["alternative"]} [{", ".join(h["evidence_ids"])}]']
        lines += ['### Investor action plan', 'Urgency: '+d.advice.get('urgency','Next review')]
        lines += ['- '+x for x in d.advice.get('next_steps',[])]
        lines += ['### Founder questions']+['- '+q for q in d.advice.get('questions',[])]
        lines += ['### Draft email — not sent',d.advice.get('email',''),d.advice.get('runway','Runway cannot be estimated from available evidence.'),'### Evidence ledger']
        for e in sorted(d.evidence,key=lambda e:e.event_date or e.publication_date or e.retrieved_at):
            lines += [f'- **{e.id}** | {e.category} | {e.status} | Event: {e.event_date or "unknown"} | Published: {e.publication_date or "unknown"} | Retrieved: {e.retrieved_at}',
                      f'  {e.fact}',f'  Source: {e.provider} — {e.source}',f'  Original value: {json.dumps(e.value,ensure_ascii=False)}',f'  Limitations: {e.limitations}; Conflicts: {e.conflicts}; Corroboration: {e.corroborating_ids}']
        lines += ['### Limitations and errors']+['- '+e for e in d.errors]
        lines += ['### Investigation decisions']+['- '+t['stage']+': '+t['detail'] for t in d.trace]
    return '\n\n'.join(lines)


def html(run):
    # Escaping is mandatory: provider/LLM content never executes as HTML.
    template=Environment(autoescape=select_autoescape(default=True)).from_string('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Startup Autopsy · Investor Briefing</title><style>body{background:#0b1019;color:#e8edf5;font:16px/1.65 system-ui;max-width:1100px;margin:48px auto;padding:24px}h1{letter-spacing:.12em;color:#58dac2}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#121c2a;padding:24px;border-radius:12px}@media print{body{background:white;color:black}pre{background:#f4f4f4}}</style><h1>STARTUP AUTOPSY</h1><p>Investor monitoring briefing · {{ timestamp }}</p><pre>{{ report }}</pre></html>''')
    return template.render(timestamp=run.created_at,report=markdown(run))
