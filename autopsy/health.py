"""Independent execution, coverage, freshness and verification summaries."""
from datetime import date


def company_health(dossier):
    evidence=dossier.evidence
    conflicts=sum(bool(e.conflicts) or e.status=='disputed/conflicting' for e in evidence)
    corroborated=sum(e.status=='corroborated observation' for e in evidence)
    dates=[e.observation_date or e.event_date for e in evidence if e.observation_date or e.event_date]
    latest=max(dates,default=None)
    stale=None
    if latest:
        try: stale=(date.today()-date.fromisoformat(latest[:10])).days>120
        except ValueError: pass
    return {'execution':dossier.status.upper().replace('COMPLETE','COMPLETED') if dossier.status=='complete' else dossier.status.upper(),
        'execution_reasons':dossier.errors,'coverage_percent':dossier.assessment.coverage,
        'verification':'Conflicting observations' if conflicts else 'Corroborated observations present; review provenance' if corroborated else 'Single-source; independently unverified' if evidence else 'Unknown',
        'conflicting_observations':conflicts,'latest_observation':latest,'observation_stale':stale,
        'retrieved_at':max((e.retrieved_at for e in evidence),default=None),
        'provider_updated_at':dossier.metadata.get('provider_updated_at'),
        'llm':dossier.metadata.get('llm_diagnostics',{'status':'Legacy run; see trace'}),
        'decision_readiness':'Evaluated separately against mandate, dated financials and deal terms; coverage is not a probability.'}
