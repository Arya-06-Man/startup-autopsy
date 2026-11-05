"""Heuristic investigation priority; never a failure probability."""
from datetime import date, timedelta
from autopsy.models import Assessment, Signal
from autopsy.evidence import number, valid_date

WEIGHTS={'workforce':.35,'leadership':.30,'hiring':.20,'business':.15}


def metric_date(e): return e.observation_date or e.event_date


def trend(evidence, category, as_of=None):
    today=as_of or date.today()
    rows=sorted([e for e in evidence if e.category==category and metric_date(e) and valid_date(metric_date(e))
                 and e.status in ('single-source observation','corroborated observation') and number(e.value)
                 and date.fromisoformat(metric_date(e))<=today], key=metric_date)
    if len(rows)<2: return None
    latest=rows[-1]
    if (today-date.fromisoformat(metric_date(latest))).days > 120: return None
    # Closest available baseline to 90 days before latest, within a 60–120 day window.
    target=date.fromisoformat(metric_date(latest))-timedelta(days=90)
    baselines=[e for e in rows[:-1] if 60 <= (date.fromisoformat(metric_date(latest))-date.fromisoformat(metric_date(e))).days <=120 and e.value>0]
    if not baselines: return None
    prior=min(baselines,key=lambda e:abs((date.fromisoformat(metric_date(e))-target).days))
    change=(latest.value-prior.value)/prior.value*100
    # -30% workforce or -50% hiring saturates category priority.
    scale=30 if category=='workforce' else 50
    severity=min(100,max(0,-change/scale*100))
    return Signal(category=category,change_pct=round(change,2),severity=round(severity,1),evidence_ids=[prior.id,latest.id],
        explanation=f'{prior.value:g} → {latest.value:g} between {metric_date(prior)} and {metric_date(latest)}: {change:+.1f}%. Provider-defined comparable count series.',
        alternatives=['Planned efficiency or role mix changes','Coverage changes or delayed profile updates'] if category=='workforce' else ['Roles filled or seasonal recruiting','Shift to contractors or a different job board'])


def assess(evidence, weights=None, as_of=None):
    weights=weights or WEIGHTS
    if set(weights)!=set(WEIGHTS) or any(v<0 for v in weights.values()) or abs(sum(weights.values())-1)>.001:
        raise ValueError('Risk weights must cover all four categories and sum to one.')
    signals=[s for c in ('workforce','hiring') if (s:=trend(evidence,c,as_of)) is not None]
    covered={s.category for s in signals}
    coverage=sum(weights[c] for c in covered)
    # Minimum 50% weighted coverage AND two comparable categories. Never fill missing categories with zero.
    score=round(sum(s.severity*weights[s.category] for s in signals)/coverage,1) if coverage>=.5 and len(covered)>=2 else None
    label='Insufficient evidence' if score is None else ('Urgent review' if score>=70 else 'Focused review' if score>=35 else 'Routine review')
    return Assessment(score=score,coverage=round(coverage*100,1),label=label,signals=signals,
        missing=[c+': dated comparable evidence unavailable' for c in weights if c not in covered])


def runway(cash,monthly_burn,as_of):
    if not number(cash) or not number(monthly_burn) or monthly_burn<=0 or not valid_date(as_of) or date.fromisoformat(valid_date(as_of))>date.today():
        raise ValueError('Supply nonnegative cash, positive monthly net burn, and a valid non-future financial date.')
    return cash/monthly_burn
