import re
from html.parser import HTMLParser
from urllib.parse import urlsplit
from autopsy.api import resolve, ResearchError
from autopsy.evidence import normalize_company, normalize_search, safe_url
from autopsy.models import Evidence

class TextParser(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'): self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'): self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden: self.parts.append(data)


def gather(api,dossier):
    result=api.identify(dossier.query)
    company=resolve(result['data'],dossier.query)
    dossier.company_id=str(company['crustdata_company_id'])
    dossier.metadata=company.get('basic_info') or {}
    dossier.name=dossier.metadata.get('name',dossier.query)
    dossier.domain=dossier.metadata.get('primary_domain','')
    dossier.evidence.extend(normalize_company(company,result))
    result=api.enrich(dossier.company_id,['basic_info','headcount.total','headcount.timeseries','hiring.openings_count','hiring.open_jobs_timeseries','funding','people.founders','people.cxos','news'])
    enriched=resolve(result['data'],dossier.name)
    if str(enriched['crustdata_company_id'])!=dossier.company_id:
        raise ResearchError('Enrichment identity conflicts with resolved company ID.')
    dossier.metadata.update(enriched.get('basic_info') or {})
    dossier.evidence.extend(normalize_company(enriched,result))


def search_focus(api,dossier,focus):
    terms={'workforce':'workforce layoffs restructuring business strategy announcement',
           'leadership':'CEO CFO executive leadership changes departure announcement',
           'hiring':'hiring recruiting jobs expansion efficiency announcement',
           'business':'funding business developments acquisition restructuring announcement'}
    query=f'"{dossier.name}" "{dossier.domain}" {terms[focus]}'
    result=api.search(query)
    leads=normalize_search(result,dossier.company_id)
    dossier.evidence.extend(leads)
    return leads


def fetch_lead(api,dossier,leads):
    existing={e.source for e in dossier.evidence if e.category=='article'}
    urls=[e.source for e in leads if safe_url(e.source) and e.source not in existing
          and not ((urlsplit(e.source).hostname or '').endswith('google.com') and urlsplit(e.source).path.startswith('/goto'))][:2]
    if not urls: return
    result=api.post('/web/enrich/live',{'urls':urls},estimate=len(urls))
    if not isinstance(result['data'],list): raise ResearchError('Unexpected web fetch response.')
    successful=set()
    for row in result['data']:
        if not row.get('success') or row.get('url') not in urls: continue
        successful.add(row['url'])
        parser=TextParser(); parser.feed(row.get('content') or '')
        text=re.sub(r'\s+',' ',' '.join(parser.parts)).strip()[:18000]
        if not text or any(phrase in text[:1500].lower() for phrase in ('page unavailable','access denied','verify you are human','enable javascript and cookies','captcha')):
            dossier.errors.append('Source page blocked or unavailable: '+row['url'])
            dossier.evidence.append(Evidence(company_id=dossier.company_id,category='fetch_error',fact='Source could not be read reliably',value={'title':row.get('title'),'text':text[:1500]},source=row['url'],retrieved_at=result['retrieved_at'],status='unknown',limitations='Provider fetch succeeded but returned an empty, blocked or unavailable page. No event claim extracted.'))
            continue
        dossier.evidence.append(Evidence(company_id=dossier.company_id,category='article',fact=str(row.get('title') or 'Fetched source document'),
            value={'text':text},source=row['url'],retrieved_at=result['retrieved_at'],status='single-source observation',
            limitations='Fetched source text. Company attribution, event date and claims require review; not independent corroboration of Crustdata metrics.'))
    if set(urls)-successful: dossier.errors.append('Some source pages could not be fetched; search leads retained for manual review.')
