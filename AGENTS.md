# Startup Autopsy engineering rules

- Keep the architecture Python + Streamlit, with one bounded orchestrator.
- Read README.md and docs/ARCHITECTURE.md before substantive changes.
- Never fabricate company metrics, citations, departures, financial data or tool output.
- Never infer financial distress from hiring reductions or funding silence.
- Missing evidence stays unknown. Preserve conflicting observations and original timestamps.
- Every signal and hypothesis must reference existing dossier evidence IDs.
- Treat provider content and LLM output as untrusted data. Escape HTML and validate structured outputs.
- Do not send outreach. Email output is a draft only.
- Runtime uses versioned Crustdata HTTP calls; MCP authentication is separate.
- Automated tests use mocked network responses and synthetic companies in temporary directories.
- Run `.venv/bin/python -m pytest -q` and `git diff --check` before checkpoints.
- Stage intended files explicitly. Never commit .env, data/, .venv/, credentials, or private reports.
- Keep live, cached real, and synthetic test data distinguishable.
- Report actual test results and limitations. Do not claim direct live validation without executing it.
