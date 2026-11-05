# Final QA audit

Baseline: clean `main` at `6967af6`, fetched origin with zero commits ahead/behind. Python 3.13.15; original 89 tests passed. Both provider credentials configured; no alternate-provider credentials configured. The application uses httpx REST, not the Google GenAI SDK.

## Priorities and findings

| Priority | Finding | Root cause / intended correction |
|---|---|---|
| P0 | Gemini listed models but failed generation | Listing was treated as compatibility and selection favored an unavailable alias/newest version. A controlled live probe of `gemini-3.5-flash` succeeded for plain text and minimal structured JSON. Shared bounded generation now prefers this advertised stable model, limits output and thinking, and preserves safe failure details. |
| P0 | Committee duplicated LLM requests and validation | Reuse the same transport and circuit breaker. Exact factual observations must reproduce a cited ledger fact; free reasoning remains explicitly a hypothesis. Reference validation does not establish semantic truth of a hypothesis. |
| P0 | All-failed investigations labeled partial | Aggregate execution from useful company results, independently of coverage, model status and readiness. Preserve failure reasons and histories. |
| P0 | Unresolved company domains | Add exact-first identification, secondary name candidates, verified alias/domain checks and explicit user disambiguation; never select an uncertain match. |
| P0 | Financial edge cases | Audit zero revenue, zero net burn, concentration normalization, extreme values and stale financial evidence; add regressions for confirmed defects. |
| P1 | Stale scenario outputs after edits | Persist inputs independently of widget lifetime and recalculate deterministic outputs; invalidate decision results when inputs change. |
| P1 | Weak discovery-to-evaluation handoff | Add explicit shortlist transfer, identity validation and persistent evaluation context. |
| P1 | Freshness/provenance unclear | Separate observation/event/publication/provider-update/retrieval fields; explicit cache bypass for refresh with retained history. |
| P1 | Raw schemas dominate workflows | Keep guided controls primary; move JSON and traces into advanced expanders, provide executive summaries. |
| P1 | Reports trust precomputed context | Recompute/validate deterministic metrics and references before export; improve Markdown readability and source links. |
| P2 | Submission recording / browser review | Use a browser if available; otherwise report the limitation and supply precise two-minute recording steps. |

## Live LLM evidence

Actual uncached diagnostic: model discovery HTTP 200, plain `OK` HTTP 200 / STOP (~2.1s), structured `{"ok":true}` HTTP 200 / STOP / schema-valid (~1.4s) using `gemini-3.5-flash`. The actual revised research `Plan` schema also returned HTTP 200 with a valid structured response (~1.5s). No SDK migration or provider switch was necessary. No unsupported claim is promoted into the factual ledger.

The first actual committee smoke call returned HTTP 503 / `UNAVAILABLE` with the provider message “This model is currently experiencing high demand.” This is an explicitly observed transient provider limitation, distinct from schema rejection or credential failure. The transport permits one bounded retry of 503 and otherwise opens a circuit with deterministic fallback; it never retries authentication, quota or output-validation failures.

A subsequent live Growth Analyst pass succeeded with a schema-valid response. A Risk Analyst response returned HTTP 200 but tried to paraphrase an assumption as a factual observation; validation rejected it and later roles used fallback. The model's role schema now permits hypotheses only: factual findings are drawn directly from the ledger by deterministic code. This avoids asking the model to establish new facts and keeps unsupported observations rejected. Full three-role live validation is recorded separately below when executed.

Official contracts consulted: [Gemini generateContent](https://ai.google.dev/api/generate-content), [structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output), [thinking configuration](https://ai.google.dev/gemini-api/docs/generate-content/thinking), [Crustdata Identify](https://docs.crustdata.com/company-docs/identify/introduction), [Company Search](https://docs.crustdata.com/company-docs/search/reference). Live results, rather than model-list position, establish tested compatibility.
