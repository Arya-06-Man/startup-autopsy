"""Credential-safe runtime smoke test and headless investigation CLI."""
import argparse
from pathlib import Path
from autopsy.config import Settings
from autopsy.api import Crustdata, ResearchError, resolve
from autopsy.storage import Store
from autopsy.llm import Planner
from autopsy.ingestion import ingest
from autopsy.orchestrator import investigate
from autopsy import reports


def main():
    parser=argparse.ArgumentParser(description='Startup Autopsy live investigation')
    parser.add_argument('companies',nargs='*',help='Company names or domains (up to five)')
    parser.add_argument('--check',metavar='DOMAIN',help='Make one authenticated Identify request and print normalized identity only')
    parser.add_argument('--check-llm',action='store_true',help='Make a real structured Gemini request and print credential-safe diagnostics')
    parser.add_argument('--check-discovery',metavar='COUNTRY',help='Search two indexed companies in a country; bypass cache')
    parser.add_argument('--output',default='data/reports')
    args=parser.parse_args()
    settings=Settings.load(); store=Store(); api=Crustdata(settings,store); planner=Planner(settings)
    try:
        if args.check_llm:
            from autopsy.models import Dossier
            result=planner.plan(Dossier(query='Integration diagnostic',name='Integration diagnostic'))
            print({'structured_response_valid':result is not None,'model':planner.model,'generation_calls':planner.calls,
                   'attempts':planner.model_attempts,'diagnostic':planner.error or ('No GEMINI_API_KEY configured' if not settings.gemini_key else None)})
            return 0 if result is not None else 1
        if args.check_discovery:
            from autopsy.discovery import search_companies
            settings.cache_hours=0
            result=search_companies(api,country=args.check_discovery,limit=2)
            print({'companies':[{'id':c.get('crustdata_company_id'),'identity':c.get('basic_info')} for c in result['companies']],
                   'mode':result['mode'],'retrieved_at':result['retrieved_at'],'has_next_page':bool(result['next_cursor'])})
            return 0
        if args.check:
            # Disable cache: this command must actually verify authentication.
            settings.cache_hours=0
            result=api.identify(ingest(args.check)[0]); company=resolve(result['data'],ingest(args.check)[0])
            basic=company.get('basic_info') or {}
            print({'company_id':company['crustdata_company_id'],'name':basic.get('name'),'domain':basic.get('primary_domain'),'mode':result['mode']})
            return 0
        queries=ingest('\n'.join(args.companies))
        run=investigate(queries,api,store,planner,lambda company,stage,detail:print(f'{company} | {stage} | {detail}'))
        root=Path(args.output); root.mkdir(parents=True,exist_ok=True)
        for suffix,content in [('html',reports.html(run)),('md',reports.markdown(run)),('json',reports.ledger(run))]:
            (root/f'{run.id}.{suffix}').write_text(content)
        print(f'Run {run.id}: {run.status}. Reports: {root}')
        return 0 if run.status=='complete' else 1
    except (ResearchError,ValueError) as exc:
        print(str(exc)); return 1
    finally: api.close(); planner.close()

if __name__=='__main__':
    raise SystemExit(main())
