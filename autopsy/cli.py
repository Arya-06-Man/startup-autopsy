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
    parser.add_argument('--output',default='data/reports')
    args=parser.parse_args()
    settings=Settings.load(); store=Store(); api=Crustdata(settings,store); planner=Planner(settings)
    try:
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
