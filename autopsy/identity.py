"""Exact identity first. Name candidates cannot silently replace a requested company."""
from autopsy.api import ResearchError,candidates,resolve
from autopsy.ingestion import normalize


class IdentityError(ResearchError):
    def __init__(self,message,options=None):
        super().__init__(message)
        self.options=options or []


def candidate_rows(result):
    candidates(result['data'])  # Validate the provider shape before presenting choices.
    rows=[]
    for entry in result['data']:
        for match in entry.get('matches',[]):
            company=match.get('company_data') or {}
            basic=company.get('basic_info') or {}
            if company.get('crustdata_company_id') is None: continue
            rows.append({'company_id':str(company['crustdata_company_id']),'name':basic.get('name'),
                'domain':basic.get('primary_domain'),'aliases':basic.get('all_domains') or [],
                'confidence':match.get('confidence_score'),'retrieved_at':result['retrieved_at'],
                'mode':result['mode'],'source':'https://api.crustdata.com/company/identify'})
    return rows


def identify_company(api,query,selection=None,name_hint=''):
    query=normalize(query)
    if selection:
        cid=str(selection.get('company_id',''))
        domain=selection.get('domain','')
        if not cid.isdigit() or not domain: raise IdentityError('Select a candidate with a canonical ID and primary domain.')
        result=api.post('/company/identify',{'crustdata_company_ids':[int(cid)],'exact_match':True,'fields':['basic_info']},estimate=0)
        company=resolve(result['data'],normalize(domain))
        if str(company['crustdata_company_id'])!=cid: raise IdentityError('Selected identity no longer matches the provider record.')
        return company,result,'Manual disambiguation; canonical ID and domain revalidated'
    first=api.identify(query)
    options=candidate_rows(first)
    try: return resolve(first['data'],query),first,'Exact domain/name or provider-documented alias'
    except ResearchError:
        pass
    # A name lookup only supplies candidates. Automatic acceptance still requires exact domain proof.
    hint=name_hint.strip() or (query.split('.')[0].replace('-',' ') if '.' in query and ' ' not in query else query)
    second=api.post('/company/identify',{'names':[hint],'exact_match':False,'fields':['basic_info']},estimate=0)
    options+=candidate_rows(second)
    if '.' in query and ' ' not in query:
        try: return resolve(second['data'],query),second,'Secondary name search corroborated by exact primary domain or documented alias'
        except ResearchError: pass
    unique={r['company_id']:r for r in options}
    raise IdentityError('Identity unresolved: no unique validated match. Compare candidates and explicitly confirm a canonical ID and domain; no company was selected.',list(unique.values())[:25])
