"""Deterministic operating/funding indicators from preserved dossier evidence."""
from datetime import date
from statistics import median


def _dated(rows, category):
    out=[]
    for e in rows:
        if e.category!=category or e.status=='disputed/conflicting' or not isinstance(e.value,(int,float)) or e.value<0: continue
        try: day=date.fromisoformat((e.observation_date or e.event_date or '')[:10])
        except ValueError: continue
        out.append((day,float(e.value),e))
    return sorted(out,key=lambda x:x[0])


def _series(rows, category):
    points=_dated(rows,category)
    def change(days):
        if not points:return None
        end=points[-1]; eligible=[p for p in points[:-1] if 0 < (end[0]-p[0]).days <= days*1.4 and (end[0]-p[0]).days >= days*.6]
        if not eligible:return None
        start=min(eligible,key=lambda p:abs((end[0]-p[0]).days-days))
        return {'value':(end[1]-start[1])/start[1] if start[1] else None,'unit':'fraction','date':end[0].isoformat(),'source':'Crustdata','evidence_ids':[start[2].id,end[2].id],'kind':'Derived from dated observations'}
    vals=[p[1] for p in points]
    acceleration=None
    if len(points)>=3:
        a,b,c=points[-3:]; dt1=(b[0]-a[0]).days;dt2=(c[0]-b[0]).days
        if dt1>0 and dt2>0: acceleration={'value':((c[1]-b[1])/dt2)-((b[1]-a[1])/dt1),'unit':'count/day²','date':c[0].isoformat(),'source':'Crustdata','evidence_ids':[a[2].id,b[2].id,c[2].id],'kind':'Derived'}
    # OLS slope uses elapsed days; minimum three observations across at least 60 days.
    regression=None
    if len(points)>=3 and (points[-1][0]-points[0][0]).days>=60:
        x=[(p[0]-points[0][0]).days for p in points]; y=[p[1] for p in points]; xm=sum(x)/len(x);ym=sum(y)/len(y);den=sum((v-xm)**2 for v in x)
        if den: regression={'value':sum((a-xm)*(b-ym) for a,b in zip(x,y))/den,'unit':'count/day','date':points[-1][0].isoformat(),'source':'Crustdata','evidence_ids':[p[2].id for p in points],'kind':'OLS derived; trend only, no forecast'}
    ewma=None
    if len(points)>=3:
        alpha=.35; level=points[0][1]
        for _,v,_ in points[1:]:level=alpha*v+(1-alpha)*level
        ewma={'value':level,'unit':'count','date':points[-1][0].isoformat(),'source':'Crustdata','evidence_ids':[p[2].id for p in points],'kind':'EWMA α=0.35'}
    changes=[(b[1]-a[1])/a[1] for a,b in zip(points,points[1:]) if a[1]>0]
    anomaly=None
    if len(changes)>=5:
        med=median(changes); mad=median(abs(x-med) for x in changes)
        current=changes[-1]
        rz=0.6745*(current-med)/mad if mad else (0 if current==med else None)
        if rz is not None: anomaly={'value':rz,'unit':'robust z','flag':abs(rz)>=3.5,'date':points[-1][0].isoformat(),'evidence_ids':[p[2].id for p in points[-2:]],'kind':'MAD; ≥5 intervals'}
    return {'latest':{'value':points[-1][1],'unit':'employees' if category=='workforce' else 'open roles','date':points[-1][0].isoformat(),'source':'Crustdata','evidence_ids':[points[-1][2].id],'kind':'Reported'} if points else None,
      'mom':change(30),'three_month':change(90),'six_month':change(180),'acceleration':acceleration,'ols_trend':regression,'ewma':ewma,'anomaly':anomaly,
      'volatility':{'value':(sum((x-sum(changes)/len(changes))**2 for x in changes)/len(changes))**.5,'unit':'fraction stddev','evidence_ids':[p[2].id for p in points],'kind':'Historical'} if len(changes)>=3 else None,
      'points':[{'date':day.isoformat(),'value':value,'evidence_id':e.id} for day,value,e in points]}


def analyze(dossier):
    if dossier is None:return {'company':'Unknown','workforce':_series([],'workforce'),'hiring':_series([],'hiring'),'funding':None,'industry':None,'coverage':0,'drivers':[],'questions':['Company dossier unavailable.']}
    ev=dossier.evidence; workforce=_series(ev,'workforce'); hiring=_series(ev,'hiring')
    funding=next((e for e in reversed(ev) if e.category=='funding_snapshot' and isinstance(e.value,dict)),None)
    f=funding.value if funding else {}; milestones=f.get('milestones') or []
    eligible=[m for m in milestones if isinstance(m,dict) and (m.get('funding_date') or m.get('date'))]
    latest=max(eligible,key=lambda m:m.get('funding_date') or m.get('date')) if eligible else None
    industry=next((e for e in ev if e.category=='identity' and isinstance(e.value,dict)),None)
    basics=industry.value if industry else {}
    latest_date=(latest or {}).get('funding_date') or (latest or {}).get('date')
    investors=(latest or {}).get('investors') or (latest or {}).get('lead_investors')
    metrics={'funding_total':{'value':f.get('total_investment_usd'),'unit':'USD','currency':'USD','date':f.get('last_fundraise_date'),'source':'Crustdata','kind':'Reported historical total','evidence_ids':[funding.id] if funding else []},
      'latest_round':{'value':(latest or {}).get('amount_usd'),'unit':'USD','currency':'USD','date':latest_date,'round_type':(latest or {}).get('round_type'),'investors':investors,'source':'Crustdata','kind':'Reported historical round','evidence_ids':[funding.id] if latest and funding else []},
      'valuation':None,'revenue':None,'traffic':None,'industry':{'value':basics.get('industries') or basics.get('industry') or basics.get('description'),'source':'Crustdata','kind':'Reported metadata','evidence_ids':[industry.id] if industry else []}}
    drivers=[]
    for label,series in [('workforce',workforce),('hiring',hiring)]:
        if series['six_month'] and series['six_month']['value'] is not None:
            drivers.append({'factor':label,'value':series['six_month']['value'],'evidence_ids':series['six_month']['evidence_ids'],'interpretation':'Observed six-month change; investigation priority only.'})
    questions=[]
    for label,value in [('revenue',metrics['revenue']),('current cash',None),('current valuation',metrics['valuation']),('web traffic',metrics['traffic'])]:
        if value is None:questions.append(f'{label.title()} is unknown; request primary dated evidence.')
    return {'company':dossier.name or dossier.query,'workforce':workforce,'hiring':hiring,'funding':metrics['funding_total'] if funding else None,'latest_round':metrics['latest_round'] if latest and funding else None,'valuation':metrics['valuation'],'revenue':metrics['revenue'],'traffic':metrics['traffic'],'industry':metrics['industry'],'metrics':metrics,'drivers':drivers,'questions':questions,'coverage':sum(v is not None for v in (workforce['latest'],hiring['latest'],funding,latest,industry)),'freshness':max((e.retrieved_at for e in ev),default=None),'evidence_ids':[e.id for e in ev]}


def compare(dossiers):
    results=[analyze(d) for d in dossiers]
    lines=[]
    for k,title in [('workforce','Workforce'),('hiring','Hiring')]:
        values=[r[k]['six_month'] for r in results]
        if len(values)==2 and all(v and v['value'] is not None for v in values):
            a,b=values; winner=results[0]['company'] if a['value']>b['value'] else results[1]['company'] if b['value']>a['value'] else 'Neither (equal)'
            lines.append(f'{winner} has stronger observed {title.lower()} growth over six months; this is an operating signal, not an investment recommendation.')
        else:lines.append(f'{title} growth cannot be compared: sufficient dated observations are unavailable for at least one company.')
    if len(results)==2 and all(r['latest_round'] and r['latest_round']['date'] for r in results):
        lines.append(f'More recent disclosed funding evidence: {max(results,key=lambda r:r["latest_round"]["date"])["company"]}; historical funding does not indicate current cash.')
    lines.append('Revenue, current valuation and traffic remain unknown unless present in dated source evidence; no winner is selected.')
    return results,lines
