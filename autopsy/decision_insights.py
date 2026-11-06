"""Deterministic, cited decision views and bounded historical trend projections."""
from datetime import date,timedelta
from autopsy.finance import readiness


def project(series,model='Dated linear regression',alpha=.35,horizon=30):
    if model not in ('Dated linear regression','EWMA'): raise ValueError('Unsupported model')
    if not 0<alpha<=1 or not 1<=horizon<=30: raise ValueError('Invalid model settings')
    points=series['points']; dates=[date.fromisoformat(p['date']) for p in points]; y=[p['value'] for p in points]
    result={'observed':points,'fitted':[],'projection':None,'backtest_mae':None,'model':model,'horizon_days':horizon,
        'limitation':'Operating-indicator extrapolation; no financial-return prediction, validated confidence interval or guarantee. Requires ≥8 observations over ≥180 days and a latest observation within 120 days.'}
    if len(points)<3:return result
    def fit(ds,values):
        if model=='EWMA':
            level=values[0]; fitted=[level]
            for value in values[1:]: level=alpha*value+(1-alpha)*level;fitted.append(level)
            return fitted,lambda d:level
        x=[(d-ds[0]).days for d in ds];xm=sum(x)/len(x);ym=sum(values)/len(values);den=sum((v-xm)**2 for v in x)
        slope=sum((a-xm)*(b-ym) for a,b in zip(x,values))/den if den else 0
        intercept=ym-slope*xm
        return [intercept+slope*v for v in x],lambda d:values[-1]+slope*(d-ds[-1]).days
    fitted,predict=fit(dates,y)
    result['fitted']=[{'date':d.isoformat(),'value':v} for d,v in zip(dates,fitted)]
    if len(points)<8 or (dates[-1]-dates[0]).days<180 or (date.today()-dates[-1]).days>120:return result
    # Chronological holdout: held-out values never enter the training fit.
    split=max(6,int(len(points)*.8));split=min(split,len(points)-1)
    _,held_predict=fit(dates[:split],y[:split])
    result['backtest_mae']=sum(abs(v-held_predict(d)) for d,v in zip(dates[split:],y[split:]))/(len(points)-split)
    target=dates[-1]+timedelta(days=horizon);value=predict(target)
    if value>=0:result['projection']={'date':target.isoformat(),'value':value}
    return result


def investor_fit(mandate,deal,dossier):
    if deal is None:return {'status':'Insufficient information to assess','reasons':['Supply genuine transaction terms, sector, stage and geography; company evidence alone does not establish investability.'],'readiness':'MORE DILIGENCE REQUIRED'}
    result=readiness(mandate,deal,dossier)
    unknown=[k for k in ('sector','stage','geography') if not getattr(deal,k)]
    if result['violations']:status='Not aligned'
    elif unknown or deal.provenance in ('MODELED ASSUMPTIONS','SYNTHETIC DEMO DATA'):status='Insufficient information to assess'
    else:status='Conditionally aligned'
    reasons=result['violations']+result['missing']+(['Missing mandate-fit inputs: '+', '.join(unknown)] if unknown else [])
    if deal.provenance!='USER-PROVIDED DATA':reasons.insert(0,'Terms provenance: '+deal.provenance+'. Genuine transaction terms require verification.')
    return {'status':status,'readiness':result['status'],'reasons':reasons or ['Primary documents and human investment approval are required.'],
        'assumption_reference':'A-'+deal.company_id}


def conclusion(dossiers):
    from autopsy.company_intelligence import analyze
    results=[analyze(d) for d in dossiers];lines=[]
    for category in ('workforce','hiring'):
        values=[(r['company'],r[category]['three_month']) for r in results]
        supported=[(name,m) for name,m in values if m and m['value'] is not None]
        if len(supported)>=2:
            lines.append('Three-month '+category+' change: '+('; '.join(f"{name} {m['value']:+.1%} as of {m['date']}" for name,m in supported))+'. Strongest observed change: '+max(supported,key=lambda p:p[1]['value'])[0]+'.')
        else:lines.append(category.title()+' growth cannot be compared across all selected companies with the available dated evidence.')
    funding=[r for r in results if r['latest_round'] and r['latest_round']['date']]
    if funding: lines.append('Most recent disclosed funding among available records: '+max(funding,key=lambda r:r['latest_round']['date'])['company']+'. Historical funding is not current cash.')
    for r in results:
        flags=[k for k in ('workforce','hiring') if r[k]['anomaly'] and r[k]['anomaly']['flag']]
        if flags:lines.append(r['company']+': investigate unusual '+', '.join(flags)+' changes against original dated records.')
    lines.append('Relative operating strength does not establish investment readiness. Revenue, valuation, cash and profitability remain unknown unless separately supplied and verified. Primary financial statements, customer retention and genuine transaction terms would most improve this decision.')
    return lines


def render(dossiers,mandate,deals):
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    from autopsy.company_intelligence import analyze
    st.markdown('### Evidence-Based Comparison Conclusion')
    for line in conclusion(dossiers):st.write(line)
    for d in dossiers:
        fit=investor_fit(mandate,next((x for x in deals if x.company_id==d.company_id),None),d)
        st.markdown('**'+(d.name or d.query)+' · '+fit['status']+'**')
        st.caption('Investment readiness: '+fit['readiness'].replace('_',' ').title())
        for reason in fit['reasons'][:5]:st.write('• '+reason)
    st.markdown('### Historical trends & qualified projections')
    company=st.selectbox('Chart company',[d.company_id for d in dossiers],format_func=lambda cid:next(d.name or d.query for d in dossiers if d.company_id==cid),key='intelligence_chart_company')
    category=st.selectbox('Operating metric',['workforce','hiring'],format_func=str.title,key='intelligence_chart_metric')
    model=st.selectbox('Trend model',['Dated linear regression','EWMA'],key='intelligence_chart_model')
    alpha=st.slider('EWMA smoothing',.05,1.,.35,.05,key='intelligence_alpha') if model=='EWMA' else .35
    horizon=st.slider('Projection horizon (days)',1,30,30,key='intelligence_horizon')
    d=next(d for d in dossiers if d.company_id==company);r=analyze(d);series=r[category];result=project(series,model,alpha,horizon)
    if result['observed']:
        fig=go.Figure();fig.add_scatter(x=[p['date'] for p in result['observed']],y=[p['value'] for p in result['observed']],name='Observed · Crustdata',mode='lines+markers')
        if result['fitted']:fig.add_scatter(x=[p['date'] for p in result['fitted']],y=[p['value'] for p in result['fitted']],name='Historical fit / smoothing',mode='lines')
        if result['projection']:
            last=result['observed'][-1];target=result['projection']
            fig.add_scatter(x=[last['date'],target['date']],y=[last['value'],target['value']],name='Illustrative estimate',mode='lines+markers',line=dict(dash='dash'))
            fig.add_shape(type='line',x0=last['date'],x1=last['date'],y0=0,y1=1,yref='paper',line=dict(dash='dot',color='#94a3b8'))
            st.caption(f"{horizon}-day estimate: {target['value']:,.1f} on {target['date']}. Historical holdout MAE: {result['backtest_mae']:,.2f} count units.")
        else:st.info('Insufficient historical data for statistically defensible forecasting. Historical observations and eligible smoothing remain visible.')
        fig.update_layout(xaxis_title='Observation / estimate date',yaxis_title='Provider-defined employee count' if category=='workforce' else 'Open roles',height=350,margin=dict(l=0,r=0,t=15,b=0))
        st.plotly_chart(fig,width='stretch',key='intelligence_history_chart')
        st.caption(f"Saved company evidence · Crustdata · {len(result['observed'])} dated observations · last observed {result['observed'][-1]['date']} · retrieved {r['freshness']}")
    else:st.info('No comparable dated observations available for this metric.')
    st.caption(result['limitation'])
