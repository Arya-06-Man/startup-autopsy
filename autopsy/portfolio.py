"""Bounded mixed-integer scenario allocation; no estimated return probabilities."""
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from autopsy.finance import readiness


def allocate(mandate, deals, dossiers=None, strategy=None):
    if len(deals)>5: raise ValueError('At most five candidate deals')
    ids=[d.company_id for d in deals]
    if len(set(ids))!=len(ids): raise ValueError('Duplicate candidate company exposures')
    strategy=strategy or {'Conservative':'downside','Moderate':'robust','Aggressive':'base'}[mandate.risk]
    if strategy not in ('downside','base','robust'): raise ValueError('Unsupported allocation strategy')
    dossiers=dossiers or {}
    exclusions={}
    candidates=[]
    for deal in deals:
        review=readiness(mandate,deal,dossiers.get(deal.company_id))
        reasons=review['violations']+review['missing']
        if any(getattr(deal,s+'_moic') is None for s in ('downside','base','upside')):
            reasons.append('Supply downside, base and upside MOIC assumptions')
        if reasons: exclusions[deal.company_id]=reasons
        else: candidates.append(deal)
    result={'strategy':strategy,'allocations':{d.company_id:0. for d in deals},'reserve':mandate.reserve,
            'uninvested':mandate.deployable,'excluded':exclusions,'violations':[],
            'assumptions':'Conditional allocations using supplied scenario MOIC, not predicted returns. Cash has 1x nominal value. All limits use total portfolio capital at cost. No full deployment requirement.',
            'sector_exposure':{},'stage_exposure':{}}
    # Existing rows deliberately aggregate duplicates rather than losing exposure.
    for field,limit in [('company_id',mandate.company_limit),('sector',mandate.sector_limit),('stage',mandate.stage_limit)]:
        for value in {getattr(h,field) for h in mandate.existing}:
            exposure=sum(h.amount for h in mandate.existing if getattr(h,field)==value)
            if exposure>mandate.capital*limit+1e-7: result['violations'].append(f'Existing {field} exposure exceeds limit: {value}')
    if result['violations'] or not candidates:
        result['reason']='No feasible new investment; resolve constraints or missing diligence.'
    else:
        n=len(candidates)
        # x in fraction of total capital, y binary active cheque; z robust surplus.
        robust=strategy=='robust'
        size=2*n+int(robust)
        objective=np.zeros(size)
        if robust: objective[-1]=-1
        else:
            objective[:n]=[-(getattr(d,strategy+'_moic')-1) for d in candidates]
        lower=np.zeros(size); upper=np.ones(size)
        if robust: lower[-1]=-np.inf; upper[-1]=np.inf
        for i,d in enumerate(candidates): upper[i]=min(mandate.max_cheque,d.investment)/mandate.capital
        rows=[]; lo=[]; hi=[]
        def add(row,l=-np.inf,h=np.inf): rows.append(row); lo.append(l); hi.append(h)
        row=np.zeros(size); row[:n]=1; add(row,h=mandate.deployable/mandate.capital)
        for i,d in enumerate(candidates):
            row=np.zeros(size); row[i]=1; row[n+i]=-upper[i]; add(row,h=0)
            row=np.zeros(size); row[i]=-1; row[n+i]=mandate.min_cheque/mandate.capital; add(row,h=0)
        for field,limit in [('company_id',mandate.company_limit),('sector',mandate.sector_limit),('stage',mandate.stage_limit)]:
            for value in {getattr(d,field) for d in candidates}:
                row=np.zeros(size)
                for i,d in enumerate(candidates): row[i]=int(getattr(d,field)==value)
                existing=sum(h.amount for h in mandate.existing if getattr(h,field)==value)
                add(row,h=limit-existing/mandate.capital)
        if robust:
            for scenario in ('downside','base','upside'):
                row=np.zeros(size); row[-1]=1
                for i,d in enumerate(candidates): row[i]=-(getattr(d,scenario+'_moic')-1)
                add(row,h=0)
        solution=milp(objective,integrality=np.array([0]*n+[1]*n+[0]*int(robust)),
                      bounds=Bounds(lower,upper),constraints=LinearConstraint(np.array(rows),lo,hi),
                      options={'time_limit':5,'mip_rel_gap':0.000001})
        if not solution.success:
            result['reason']='Solver did not establish an optimal feasible allocation; capital remains uninvested.'
        else:
            # Do not publish solver outputs if any normalized hard constraint is violated.
            values=np.array(rows) @ solution.x
            if np.any(values < np.array(lo)-1e-7) or np.any(values > np.array(hi)+1e-7):
                result['reason']='Solver output failed hard-constraint validation; capital remains uninvested.'
                return result
            for i,d in enumerate(candidates): result['allocations'][d.company_id]=max(0.,float(solution.x[i])*mandate.capital)
            result['uninvested']=max(0.,mandate.deployable-sum(result['allocations'].values()))
            result['reason']='Maximize worst-case surplus over cash across all supplied scenarios.' if robust else f'Maximize supplied {strategy} scenario surplus over cash.'
            result['modeled_new_capital_proceeds']={s:sum(result['allocations'][d.company_id]*getattr(d,s+'_moic') for d in candidates)+result['uninvested'] for s in ('downside','base','upside')}
    for field in ('sector','stage'):
        exposure={}
        for h in mandate.existing: exposure[getattr(h,field)]=exposure.get(getattr(h,field),0)+h.amount
        for d in deals: exposure[getattr(d,field)]=exposure.get(getattr(d,field),0)+result['allocations'][d.company_id]
        result[field+'_exposure']=exposure
    return result


def stress(allocations, deals, moic_multiplier=1., failed_ids=()):
    if not 0<=moic_multiplier<=2: raise ValueError('Invalid scenario multiplier')
    lookup={d.company_id:d for d in deals}
    rows=[]
    for company_id,amount in allocations.items():
        d=lookup[company_id]
        if d.base_moic is None: raise ValueError('Missing supplied base outcome')
        value=0. if company_id in failed_ids else amount*d.base_moic*moic_multiplier
        rows.append({'company_id':company_id,'capital':amount,'modeled_proceeds':value,'modeled_loss':max(0.,amount-value)})
    return {'holdings':rows,'capital_at_risk':sum(r['modeled_loss'] for r in rows),
            'proceeds':sum(r['modeled_proceeds'] for r in rows),'label':'MODELED ASSUMPTIONS; no statistical correlations or failure probabilities.'}
