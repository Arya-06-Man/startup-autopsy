# Hackathon submission checklist

## Implemented and tested

- [x] Streamlit dashboard, CSV/paste intake, company dossiers and evidence timeline
- [x] Versioned Python Crustdata integration and strict identity resolution
- [x] Bounded evidence-dependent follow-up research and readable source fetches
- [x] Optional structured Gemini planner with deterministic fallback
- [x] Provenance, dated observations, deduplication and conflicting-count preservation
- [x] Transparent workforce/hiring priority and missing-evidence safeguards
- [x] Investor actions, founder questions and draft-only outreach
- [x] HTML, Markdown and JSON deliverables
- [x] Local persistence, caching, budgets, retries and partial failure handling
- [x] 45 executed passing tests; synthetic test fixtures isolated from live output
- [x] Empty, populated and actual cached real dashboard AppTest checks
- [x] Connected Crustdata live requests and actual-response normalization/report validation
- [x] README, environment example, sample CSV, architecture and demo script
- [x] Tested milestone commits pushed to existing GitHub repository

## Must finish before claiming complete live validation

- [ ] Add CRUSTDATA_API_KEY locally and execute a direct Python Identify check
- [ ] Execute a complete direct Python HTTP investigation and inspect outputs
- [ ] Verify Gemini against an accessible live model if used in the presentation
- [ ] Visual browser review at presentation resolution (browser unavailable during build)
- [ ] Record and rehearse the actual demo
- [ ] Verify latest GitHub Actions result
- [ ] Review provider licensing before sharing exported source text

## Judge-facing distinctions

- End-to-end execution: intake → research → verification → assessment → intervention → report.
- Facts: each scored trend cites actual dated ledger entries; no fabricated metrics or citations.
- Robustness: budgets, partial failures, missing data, blocked sources, cache and fallback.
- Customer value: a finished portfolio-monitoring work product, including explicit next evidence requests.
- Demo: show decisions, evidence IDs, limitations and downloaded deliverables.

## Known limitations to disclose

No bankruptcy prediction. Numeric leadership/adverse-business scoring and automatic semantic article contradiction detection are not implemented. No independent corroboration is automatically asserted. Cash and burn are never inferred. Credit ceilings are estimates, not guaranteed billing caps. Runtime rate limits are per client, not shared across sessions. Interrupted runs reopen preserved work but do not automatically resume in the background. Product is for local use without production authentication or tenant isolation.
