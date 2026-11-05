"""Verified 2025-11-01 indexed Company Search contract, credit-bounded pages."""
from autopsy.api import ResearchError
from autopsy.mandate import country_key,category_key

FIELDS=['crustdata_company_id','basic_info.name','basic_info.primary_domain','taxonomy.professional_network_industry',
        'locations.country','headcount.total','headcount.growth_percent','funding.last_round_type','funding.total_investment_usd','hiring.openings_count','metadata.updated_at']


def search_companies(api, industry='', country='', stage='', min_headcount=0, growth=None, cursor=None, limit=10):
    if not 1<=limit<=20: raise ValueError('Discovery pages are bounded to 20 companies')
    conditions=[]
    for field,value in [('basic_info.industries',industry),('locations.country',country),('funding.last_round_type',stage)]:
        if value: conditions.append({'field':field,'type':'in','value':[value]})
    if min_headcount: conditions.append({'field':'headcount.total','type':'=>','value':min_headcount})
    if growth is not None: conditions.append({'field':'headcount.growth_percent.6m','type':'=>','value':growth})
    if not conditions: raise ValueError('Select at least one company discovery filter')
    payload={'filters':{'op':'and','conditions':conditions},'fields':FIELDS,
             'sorts':[{'field':'crustdata_company_id','order':'asc'}],'limit':limit}
    if cursor: payload['cursor']=cursor
    result=api.post('/company/search',payload,estimate=limit*1.5)
    data=result['data']
    if not isinstance(data,dict) or not isinstance(data.get('companies'),list): raise ResearchError('Unexpected Company Search response; no records substituted')
    return {'companies':data['companies'],'next_cursor':data.get('next_cursor'),'retrieved_at':result['retrieved_at'],
            'mode':result['mode'],'filters':payload['filters']}


def rows(page, mandate=None):
    result=[]
    for c in page['companies']:
        basic=c.get('basic_info') or {}; head=c.get('headcount') or {}; funding=c.get('funding') or {}
        countries=(c.get('locations') or {}).get('country') or []
        if isinstance(countries,str): countries=[countries]
        industries=(c.get('taxonomy') or {}).get('professional_network_industry') or []
        if isinstance(industries,str): industries=[industries]
        gaps=['Financial statements and deal terms not supplied','Industry taxonomy is not proof of business model fit']
        fit=[]
        if mandate:
            if mandate.geographies: fit.append('Geography matches' if any(country_key(x) in [country_key(v) for v in mandate.geographies] for x in countries) else 'Geography requires review')
            if mandate.stages: fit.append('Stage matches' if category_key(funding.get('last_round_type','')) in [category_key(v) for v in mandate.stages] else 'Stage requires review')
            if mandate.sectors: fit.append('Sector thesis requires business-model verification')
        result.append({'ID':str(c.get('crustdata_company_id','')),'Company':basic.get('name'),
                       'Domain':basic.get('primary_domain'),'Sector':', '.join(industries),
                       'Geography':', '.join(countries),'Headcount':head.get('total'),
                       '6m growth %':(head.get('growth_percent') or {}).get('6m'),
                       'Funding stage':funding.get('last_round_type'),'Funding USD':funding.get('total_investment_usd'),
                       'Open roles':(c.get('hiring') or {}).get('openings_count'),
                       'Retrieved':page['retrieved_at'],'Provider updated':(c.get('metadata') or {}).get('updated_at') or c.get('updated_at'),'Provider observation date':'Not supplied in search projection',
                       'Screening':'; '.join(fit) or 'Mandate review pending','Unresolved':'; '.join(gaps),
                       'Source':'SINGLE-SOURCE OBSERVATIONS · '+page['mode']})
    return result
