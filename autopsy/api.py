"""Versioned Crustdata HTTP client. Sequential calls enforce endpoint rate limits."""
import time
import httpx
from autopsy.models import now

class ResearchError(Exception):
    pass

class Crustdata:
    BASE = 'https://api.crustdata.com'

    def __init__(self, settings, store, transport=None):
        self.settings, self.store = settings, store
        self.http = httpx.Client(base_url=self.BASE, timeout=45, transport=transport,
            headers={'Authorization': 'Bearer ' + settings.api_key, 'x-api-version': '2025-11-01'})
        self.calls = 0
        self.estimated_credits = 0.0
        self.actual_credits = 0.0
        self.actual_reported = 0
        self.cache_hits = 0
        self.last = {}
        self.stopped = False
        self.audit = []
        self.transport = transport

    def close(self):
        self.http.close()

    def usage(self):
        return dict(api_calls=self.calls, cache_hits=self.cache_hits,
                    estimated_credits=self.estimated_credits, actual_credits=self.actual_credits,
                    actual_credit_headers=self.actual_reported, audit=self.audit)

    def post(self, path, payload, estimate=1):
        cached = self.store.cached(path, payload, self.settings.cache_hours)
        if cached:
            self.cache_hits += 1
            return {**cached, 'mode': 'CACHED REAL DATA'}
        if not self.settings.api_key:
            raise ResearchError('Missing CRUSTDATA_API_KEY. Add it to .env, then launch again.')
        if self.stopped:
            raise ResearchError('API halted after authentication or credit failure.')
        for attempt in range(3):
            if self.calls >= self.settings.max_calls or max(self.estimated_credits, self.actual_credits) + estimate > self.settings.max_credits:
                raise ResearchError('Investigation budget reached. Increase the call or credit limit for a new run.')
            # 10/min web, conservative 30/min other endpoints, including retries.
            interval = 6.1 if path.startswith('/web/') else 2.1
            delay = max(0, interval - (time.monotonic() - self.last.get(path, 0)))
            if delay and self.transport is None:
                time.sleep(delay)
            self.last[path] = time.monotonic()
            self.calls += 1
            self.estimated_credits += estimate
            try:
                response = self.http.post(path, json=payload)
            except httpx.TransportError:
                if attempt < 2:
                    if self.transport is None: time.sleep(2 ** attempt)
                    continue
                raise ResearchError('Crustdata timed out or could not connect after three bounded attempts.')
            self.audit.append({'endpoint':path,'status':response.status_code,'at':now(),'estimated_credits':estimate})
            if response.headers.get('X-Credits-Used'):
                try:
                    self.actual_credits += float(response.headers['X-Credits-Used'])
                    self.actual_reported += 1
                except ValueError:
                    pass
            if response.status_code in (401,402):
                self.stopped = True
            if response.status_code == 403:
                try:
                    error=response.json().get('error',{})
                    if isinstance(error,dict) and error.get('type') == 'insufficient_credits':
                        self.stopped = True
                except ValueError: pass
            if response.status_code in (429,500,502,503,504) and attempt < 2:
                if self.transport is None:
                    try: delay = min(20, max(1, float(response.headers.get('Retry-After', 2 ** (attempt+1)))))
                    except ValueError: delay = 2 ** (attempt+1)
                    time.sleep(delay)
                continue
            if response.is_error:
                messages = {400:'Request rejected; check endpoint schema/field access.',401:'Invalid Crustdata API key; update .env.',402:'Crustdata credits exhausted; replenish credits.',403:'Endpoint or fields unavailable, or credits exhausted; check your Crustdata plan.',404:'No company record found.',429:'Rate limit reached; try again later.'}
                detail=''
                if response.status_code==400:
                    try:
                        error=response.json().get('error',{})
                        message=error.get('message','') if isinstance(error,dict) else str(error)
                        detail=' '+str(message).replace(self.settings.api_key,'[redacted]')[:500]
                    except (ValueError,AttributeError): pass
                raise ResearchError(f'Crustdata HTTP {response.status_code}: ' + messages.get(response.status_code,'Provider unavailable; retry later.')+detail)
            try:
                data = response.json()
            except ValueError as exc:
                raise ResearchError('Crustdata returned invalid JSON.') from exc
            result = dict(data=data, retrieved_at=now(), mode='LIVE DATA', endpoint=path)
            self.store.put_cache(path, payload, result)
            return result
        raise ResearchError('Retry limit reached.')

    def identify(self, query):
        field = 'domains' if '.' in query and ' ' not in query else 'names'
        return self.post('/company/identify', {field:[query]}, estimate=0)

    def enrich(self, company_id, fields):
        # Conservative reservation per call; account pricing may vary by field grants.
        return self.post('/company/enrich', {'crustdata_company_ids':[int(company_id)], 'fields':fields}, estimate=5)

    def search(self, query):
        return self.post('/web/search/live', {'query':query, 'sources':['web','news']}, estimate=1)


def candidates(response):
    if not isinstance(response, list):
        raise ResearchError('Unexpected company response: expected the documented top-level array.')
    result=[]
    for entry in response:
        for match in entry.get('matches',[]):
            company=match.get('company_data') or {}
            if company.get('crustdata_company_id') is not None:
                result.append(company)
    return result


def resolve(response, query):
    matches=candidates(response)
    if '.' in query and ' ' not in query:
        matches=[m for m in matches if (m.get('basic_info',{}).get('primary_domain') or '').lower().removeprefix('www.') == query]
    unique={str(m['crustdata_company_id']):m for m in matches}
    if not unique: raise ResearchError('No exact company match. Try its primary website domain.')
    if len(unique)>1:
        names=', '.join(m.get('basic_info',{}).get('name','Unknown') + ' (' + str(m.get('basic_info',{}).get('primary_domain','')) + ')' for m in unique.values())
        raise ResearchError('Ambiguous company identity. Enter a specific domain. Candidates: ' + names)
    return next(iter(unique.values()))
