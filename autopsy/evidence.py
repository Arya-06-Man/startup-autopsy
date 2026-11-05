"""Normalize only documented fields; retain original values and API provenance."""
import json
import math
from datetime import date
from urllib.parse import urlsplit, urlunsplit
from autopsy.models import Evidence


def valid_date(value):
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        return None


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value >= 0


def normalize_company(company, result):
    cid=str(company['crustdata_company_id'])
    source=f"https://api.crustdata.com{result['endpoint']}#company={cid}"
    evidence=[]
    def object_section(key):
        value=company.get(key)
        if value is None: return {}
        if not isinstance(value,dict): raise ValueError('Malformed provider '+key+' section; expected an object.')
        return value
    updated=object_section('metadata').get('updated_at') or company.get('updated_at')
    def add(category,fact,value,event_date=None,suffix='',observation_date=None):
        evidence.append(Evidence(company_id=cid,category=category,fact=fact,value=value,
            source=source+suffix,event_date=valid_date(event_date),observation_date=valid_date(observation_date),
            provider_updated_at=updated,data_mode=result.get('mode','Unknown'),retrieved_at=result['retrieved_at']))
    basic=object_section('basic_info')
    if basic:
        add('identity','Resolved company identity and provider metadata',basic)
    for section,key,category in [('headcount','employee_count','workforce'),('hiring','open_jobs','hiring')]:
        obj=object_section(section)
        rows=obj.get('timeseries' if section=='headcount' else 'open_jobs_timeseries') or []
        if isinstance(rows,list):
            for row in rows:
                if isinstance(row,dict) and number(row.get(key)) and valid_date(row.get('date')):
                    add(category,f"Provider {key}: {row[key]}",row[key],observation_date=row['date'],suffix='/'+section)
        current=obj.get('total' if section=='headcount' else 'openings_count')
        if number(current):
            add(category+'_snapshot','Current provider snapshot (effective date unknown)',current,suffix='/'+section)
    funding=object_section('funding')
    if funding:
        add('funding_snapshot','Provider funding summary; funding silence does not establish a cash shortage',funding, suffix='/funding')
    for row in funding.get('milestones') or []:
        if isinstance(row,dict):
            add('funding','Provider funding milestone',row,row.get('funding_date') or row.get('date'),'/funding')
    people=object_section('people')
    if isinstance(people,dict):
        for group in ('founders','cxos','decision_makers'):
            for row in people.get(group) or []:
                add('leadership_snapshot',f'Provider {group} profile; presence does not establish retention or departure',row,suffix='/people')
    # Unknown news schemas remain auditable raw observations, never silently interpreted as events.
    news=company.get('news')
    if news:
        add('business_raw','Provider news section; requires article-level review',news,suffix='/news')
        if isinstance(news,list):
            for row in news:
                if isinstance(row,dict) and safe_url(row.get('article_url','')):
                    evidence.append(Evidence(company_id=cid,category='news_observation',fact=str(row.get('article_title') or 'Provider news lead'),
                        value=row,source=row['article_url'],publication_date=valid_date(row.get('article_publish_date')),
                        provider_updated_at=updated,data_mode=result.get('mode','Unknown'),retrieved_at=result['retrieved_at'],
                        status='unknown',limitations='Provider news lead, not a verified company event. Publication does not establish event date.'))
    return evidence


def normalize_search(result,cid):
    data=result['data']
    if not isinstance(data,dict) or data.get('success') is False:
        raise ValueError('Web search returned an unsuccessful or unexpected response.')
    if not isinstance(data.get('results'),list): raise ValueError('Malformed web search results; expected a list.')
    evidence=[]
    for row in data.get('results',[])[:10]:
        if not isinstance(row,dict) or not safe_url(row.get('url','')): continue
        evidence.append(Evidence(company_id=cid, category='research_lead',
            fact=str(row.get('title') or 'Search result'),value=row,source=row['url'],
            publication_date=valid_date(row.get('publication_date')),retrieved_at=result['retrieved_at'],
            data_mode=result.get('mode','Unknown'),
            status='unknown', limitations='Search lead; snippet may be incomplete or misattributed. Not an established company event.'))
    return evidence


def safe_url(url):
    try:
        parsed=urlsplit(url)
        return parsed.scheme in ('http','https') and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def canonical_url(url):
    if not safe_url(url): return url
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc.lower(),p.path.rstrip('/'),'',''))


def verify(evidence):
    seen={}; unique=[]
    for item in evidence:
        key=(item.company_id,item.category,item.observation_date or item.event_date,json.dumps(item.value,sort_keys=True),canonical_url(item.source))
        if key not in seen:
            unique.append(item); seen[key]=item.id
    groups={}
    for e in unique:
        if e.category in ('workforce','hiring') and (e.observation_date or e.event_date):
            groups.setdefault((e.company_id,e.category,e.observation_date or e.event_date),[]).append(e)
    for items in groups.values():
        if len({json.dumps(e.value,sort_keys=True) for e in items}) > 1:
            for e in items:
                e.status='disputed/conflicting'
                e.conflicts=[x.id for x in items if x.id!=e.id]
                e.limitations='Same dated metric has conflicting observations; excluded from scoring.'
    # Matching text or distinct hostnames do not establish source independence.
    return unique


def validate_refs(ids,evidence):
    known={e.id for e in evidence}
    if not ids or not set(ids) <= known:
        raise ValueError('Unsupported or missing evidence references.')
    return ids
