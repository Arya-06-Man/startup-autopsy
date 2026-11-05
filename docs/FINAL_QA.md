# Final QA audit

Baseline: clean `main` at `6967af6`, fetched origin with zero commits ahead/behind. Python 3.13.15; original 89 tests passed. Both provider credentials configured; no alternate-provider credentials configured. The application uses httpx REST, not the Google GenAI SDK.

## Priorities and findings

| Priority | Finding | Root cause / intended correction |
|---|---|---|
| P0 | Gemini listed models but failed generation | Listing was treated as compatibility and selection favored an unavailable alias/newest version. A controlled live probe of `gemini-3.5-flash` succeeded for plain text and minimal structured JSON. Shared bounded generation now prefers this advertised stable model, limits output and thinking, and preserves safe failure details. |
| P0 | Committee duplicated LLM requests and validation | Reuse the same transport and circuit breaker. Generated roles permit hypotheses only; factual findings come directly from the source ledger. Reference validation does not establish semantic truth of a hypothesis. |
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

## Live company investigation and provenance

Fresh run `1cf447edf997`: `LIVE DATA`, execution complete, four direct Python Crustdata calls (Identify + Enrich for Retool `633593` and Razorpay `897127`), zero web follow-up iterations. Both companies used validated Gemini plans; one transient 503 recovered on the single retry. Retool yielded 350 observations and Razorpay 417; scored coverage was 55% each, separate from execution success. Cash, valuation and financial statements were not inferred.

Direct two-result Company Search succeeded for `IND`, with a next cursor. The live Search endpoint rejected the documentation's top-level `updated_at` projection and explicitly suggested `metadata.updated_at`; that corrected projection succeeded. Enrich accepted `updated_at` but did not supply an update timestamp in this run. Missing provider dates remain unknown. Fresh retrieval is never represented as a fresh underlying observation.

A later combined-filter live search (`IND`, `Software Development`, `seed`, headcount ≥10, limit 2) also succeeded with real results racetrack.ai (`6403`) and Rein Games Private Limited (`6876`) and a next cursor. These are provider screening observations, not verified investment readiness. No enrichment was automatically performed for those search results.

New count records distinguish observation dates from event dates; the trend engine reads observation dates with backward compatibility for original records. News publication, provider update, retrieval time and cached/live mode remain separate. Refresh bypasses cache without deleting histories. Unresolved identities retain candidate comparisons and require user confirmation followed by canonical ID/domain revalidation. An all-failed run is failed; mixed useful/failed work is partial; absent optional financials or LLM fallback alone do not fail execution.

An uncached exact `notion.so` Identify check still had no validated domain match; it remains unresolved rather than silently mapped to another business. Retool and Razorpay are the two companies actually validated in this session. The identity/caching/status milestone passed **106 tests** including explicit manual revalidation, alias handling, failed portfolios and optional model failures.

## Verified decision workflow and financial regressions

- Actual Gemini diagnostic committee: all three role passes returned HTTP 200, schema-valid results with supported references using `gemini-3.5-flash`. No fallback was used in the successful run. Earlier transient overload and invalid-output attempts remain documented above.
- Actual private decision memo used the two real dossiers from `1cf447edf997`, a ₹10 crore mandate, explicitly **MODELED ASSUMPTIONS** for illustrative entry terms and an independently labeled hypothetical War Room. No real financial statements or company cash values were invented. The actual live Gemini committee completed all three passes; both deals remained **MORE DILIGENCE REQUIRED**, conditional allocation **zero**. HTML, Markdown and JSON files were generated under ignored `data/reports/final-qa/decision-memo/`.
- Full Streamlit AppTest journey A–F uses mocked providers and synthetic companies in a temporary directory: guided mandate → discovery → watchlist → explicit Add to Evaluation → two-company investigation → guided terms → allocation → reactive cash scenario → explicit scenario-to-deal handoff → revised allocation → three committee roles → all exports → original frozen-evidence decision replay. It verifies a ₹4 crore allocation changes to ₹2 crore after an actual downside-assumption change, then restores ₹4 crore on replay. This is automated workflow validation, not a claim of a browser-recorded live investment decision.
- That workflow test exposed an existing P0 defect: the discovery form key collided with the saved filters session-state key, crashing a successful search. The form now has a separate key. A default integer credit budget also caused a mixed numeric-type Streamlit error; budget inputs now consistently use floats.
- Revenue falling to zero now calculates −100% growth. Zero net burn has no finite depletion runway. Case/whitespace variants cannot bypass sector/stage/company exposure aggregation. Partial cheques enforce supplied minimum ownership targets. Non-finite output and overflow are rejected. All are regression-tested.
- Reports revalidate computed financial metrics, original ledger references, terms identities, capital conservation, reserves and exposure/cheque constraints. They do not export substituted sources or stale calculations. Source links are escaped and restricted to HTTP(S), and observation/event/publication/provider-update/retrieval fields remain distinct.
- Replay now identifies individual changed list fields, such as `deals[0].terms.valuation`, rather than dumping a complete changed deal list. It restores frozen evidence and clears unrelated later scenarios when reopening a decision that had no War Room.

## Release checks and remaining gates

Full suite: **126 tests passed** before the final documentation checkpoint; compilation and `git diff --check` passed. Dependency consistency check reported no broken requirements. Final checkpoint results and CI are recorded in the delivery response.

The local Streamlit server health endpoint returned **HTTP 200 / ok**. Browser skill setup reported no available browser, and discovery returned an empty browser list. Therefore no visual inspection or video recording is claimed. The repository was verified **PUBLIC** through GitHub. Architecture and demo instructions are publicly accessible repository documents. Actual deadline/video-upload status must be confirmed by the submitting team; neither was invented.

Known boundaries: hypotheses are not verified facts; no automatic semantic truth verification, SAFE/note/preferred conversion, legal waterfall, financial-document extraction, multi-round cap table or production authentication. Current scenario stress covers new allocations; existing holdings affect concentration and budget. The optimizer does not silently renegotiate an out-of-mandate proposed cheque. No trades or outreach are executed.

Final malformed-provider regression sweep: four new tests first reproduced failures for malformed nested identity, funding, web-search and fetched-page records. Shape validation now turns these into explicit per-company/page errors, preserves subsequent readable pages, and continues later companies. The complete suite reached **126 passing tests**. No provider request contract changed in this hardening step.
