# VCOS baseline audit

Audit executed November 6, 2026 (Asia/Kolkata); provider retrieval dates retain UTC.

- Inspected repository, history and existing Python/Streamlit architecture. Working tree initially clean at `21453dc`; fetched `origin/main`, zero commits ahead/behind.
- Original suite: **45 passed**. Tests use mocked requests and synthetic companies, never live credentials.
- Direct uncached Python Identify succeeded for Retool (`633593`). A bounded real investigation completed, preserving provider evidence and source dates in ignored local `data/`. Scored coverage was 55%, distinct from execution success. Private reports are not committed.
- Direct uncached Company Search succeeded with two India results and a next-page cursor. An initial projection was rejected: `basic_info.industries` is filterable but not returnable. Corrected projection uses `taxonomy.professional_network_industry`. Country, identity, headcount, growth, funding and hiring projections were accepted. Missing values remain unknown.
- Gemini model discovery succeeded. Actual structured generation attempts encountered HTTP 404, HTTP 503 and a network timeout. No successful live structured response was established during the initial audit. Subsequent validation results belong in README. No fallback is described as Gemini success.

## Root causes and fixes

`PARTIAL` previously combined optional LLM errors with collection failures. Optional model failures now appear in explicit model diagnostics and the decision trace; they no longer mark an otherwise completed evidence collection partial. Provider errors still produce partial/failed execution. Evidence coverage is unchanged; no calibrated decision-confidence probability is claimed.

The default 20 attempts, 30 estimated credits and two research iterations are shared across up to five companies. Large shortlists can exhaust this bounded budget. Blocked source pages and ambiguous identity also remain visible partial results. Raising limits is an explicit investor choice, not an automatic relaxation.

Cache hits preserve original retrieval timestamps. Expired, malformed, timezone-naive and future-dated cache records are now misses. This prevents future timestamps from keeping data eligible indefinitely. Histories are retained; old runs are never rewritten by these changes.

Gemini selection previously trusted discovery order. Automatic selection now prioritizes an advertised stable Flash alias, then newer non-preview text models, and tries at most three candidates after 404/503. Explicit model configuration is honored. Diagnostics expose safe status categories and model names without URLs, request headers or keys. The final stable-alias generation check timed out; no successful live generation is claimed.

## Contract sources

- [Company Search](https://docs.crustdata.com/company-docs/search/reference): filters, fields, stable sorts and cursor pagination.
- Connected Crustdata `list_search_fields(dataset="company")`: filterable versus returnable fields, verified during this session.
- [Company Identify](https://docs.crustdata.com/company-docs/identify/introduction) and [Enrichment](https://docs.crustdata.com/company-docs/enrichment/reference).
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output): structured generation is validated locally; advertised model availability is not assumed to mean successful generation.

## Reproduce

```bash
.venv/bin/python -m autopsy.cli --check retool.com
.venv/bin/python -m autopsy.cli --check-llm
.venv/bin/python -m autopsy.cli --check-discovery IND
.venv/bin/python -m autopsy.cli retool.com
.venv/bin/python -m pytest -q
git diff --check
```

Checks make real calls and may consume provider credits. All automated tests remain offline. Missing credentials are actionable limitations, never synthetic substitution.
