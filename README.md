# Startup Autopsy VCOS
### Autonomous Venture Capital Intelligence & Decision Platform

**Discover → Investigate → Verify → Compare → Stress-test → Allocate → Challenge → Decide → Report**

Startup Autopsy replaces substantial first-pass VC analyst work: company discovery, evidence investigation, mandate screening, deal comparison, scenario calculations, conditional capital allocation, structured committee challenge, decision replay and investment memo preparation. It extends the existing bounded investigator and evidence ledger; it never executes investments or sends outreach.

Built for **ContextCon 04, IIT Kanpur · Investing · Services, Replaced**.

Public repository: [Arya-06-Man/startup-autopsy](https://github.com/Arya-06-Man/startup-autopsy). See the [final QA audit](docs/FINAL_QA.md) for actual provider results, workflow validation and limitations.

## Use the decision workspace

The primary sidebar is always visible above connection settings. **Overview** is the default entry point; research, investment decisions and documents have dedicated pages.

1. **Overview / Company Search:** submit a company name or website in the prominent search bar. Lookup uses the existing Crustdata identity service, with bounded calls and explicit refresh. Ambiguous matches require candidate comparison and confirmation; no suggestions are invented. Results offer **View Company**, **Investigate**, **Add to Compare** and **Add to Watchlist**. Typing and ordinary navigation do not trigger lookups.
2. **Investment Mandate:** use **Create Investment Mandate** from the onboarding guide, or open the sidebar page. Review budget, reserves, preferences and hard constraints, then save locally. Advanced inputs remain available in the validated JSON editor. The compact first-use guide can be skipped; that preference persists locally.
3. **Startup Discovery:** filter the documented Crustdata index by industry, country, funding round, headcount and growth. The concise sortable results table keeps extra metrics and source dates in an expander. Select 2–5 companies, save a watchlist or add them to evaluation. Only explicitly investigated companies are deeply enriched.
4. **Due Diligence / Company Overview:** launch the preserved investigator from a search result or upload a portfolio. Open company dossiers for executive context, actual dated operating trends, source details, financial unknowns and next questions. **Investigation History** reopens original runs without deleting or relabeling them.
5. **Deal Comparison:** configure supplied investment terms in place, compare companies side by side, inspect sources and missing diligence, and save/reopen named comparisons. Continue directly to Portfolio Lab, VC War Room or Investment Committee. Financials remain user-provided; document labels are attestations, not machine verification.
6. **Portfolio Lab:** review total budget, deployable capital, follow-on reserves and hard limits, then compute allocations and alternatives. The optimizer may invest in neither. Existing holdings remain included at cost; missing critical evidence and unsupported instruments exclude a deal.
7. **VC War Room:** assumptions sit on the left in Operations, Financing and Returns tabs; calculated cash paths and outcome comparisons appear on the right. Inputs persist and results recalculate when changed. Explore 1/3/5/7/10-year horizons and funding-delay sensitivity. Explicitly apply modeled outcomes only to a matching opportunity, then recompute allocation. Saved scenarios and decision replay preserve actual previous inputs.
8. **Investment Committee:** guided prerequisite states lead to mandate creation or deal comparison. Challenge the thesis through three structured roles from one provider, or visibly labeled fallback checklists. **Generate Report** saves a validated memo and opens Reports. Decision snapshots retain frozen evidence and actual before/after differences.
9. **Reports:** browse original research briefings, saved decision snapshots and committee memos. **Download PDF** creates a native A4 document with embedded fonts, repeating table headers, source links, page numbers and deterministic financial tables. **Print Report** downloads the same print-ready PDF; open it and use the viewer's Print command. HTML preview, Markdown and JSON exports remain available. PDF source appendices show cited, identity and conflicting records; the JSON retains the entire original ledger.

All UI workspace records—including company identities, comparisons, onboarding preferences and reports—stay under ignored `data/vcos/`. Reports and financial inputs are never committed. PDF generation uses ReportLab; QA uses pypdf and PyMuPDF. ISO currency codes avoid missing currency glyphs. Unsupported scripts are explicitly shown as Unicode code points; configure `PDF_FONT_PATH` and `PDF_FONT_BOLD_PATH` for additional font coverage.

Capital means **total portfolio capital at cost**, including existing holdings. Exposure limits use that denominator. Deployable capital = total minus existing holdings, follow-on reserve and liquidity buffer. Currency conversion is never implicit.

Moderate risk defaults to maximizing the worst-case nominal surplus over cash across supplied scenarios; Conservative uses supplied downside and Aggressive uses supplied base. These are scenario objectives, not inferred probability distributions. With a downside below 1x, a robust optimizer can correctly choose cash. Conditional allocations are capped at supplied cheque sizes; all hard limits remain enforced.

Readiness is separate from execution and evidence coverage: **OUTSIDE MANDATE**, **MORE DILIGENCE REQUIRED**, **CONDITIONALLY REVIEWABLE**, or **READY FOR COMMITTEE REVIEW**. The last requires the user's explicit primary-document verification attestation; it does not mean investment approval or independent machine verification.

Private mandates, snapshots and watchlists live under ignored `data/vcos/`. No synthetic company financials are populated in the live UI. Automated tests use distinctly labeled synthetic fixtures in temporary directories.

## Run locally on macOS

Requires Python 3.11+ (this workspace was tested with Python 3.13).

```bash
cd startup-autopsy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` locally and set `CRUSTDATA_API_KEY`. Never paste or commit credentials. Gemini is optional; without it the evidence-driven deterministic investigator and reports work.

```bash
streamlit run app.py
```

Or without activating the environment:

```bash
.venv/bin/streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open **http://127.0.0.1:8501**. Start in Overview with company search or create an Investment Mandate. Due Diligence accepts live search or up to five names/domains for investigation, including [samples/portfolio.csv](samples/portfolio.csv). Prefer primary domains to avoid ambiguous names. The investigation button requires an API key. Previous real runs remain available in Due Diligence and Investigation History.

`requirements.txt` supports compatible installations across Python versions. `requirements-lock.txt` records the exact environment tested here; its transitive pins may require Python 3.13 and are not the default installation path.

## Validate the real integration

```bash
.venv/bin/python -m autopsy.cli --check retool.com
.venv/bin/python -m autopsy.cli --check-discovery IND
.venv/bin/python -m autopsy.cli --check-llm
.venv/bin/python -m autopsy.cli --diagnose-llm --model gemini-3.5-flash
.venv/bin/python -m autopsy.cli --check-committee --model gemini-3.5-flash
.venv/bin/python -m autopsy.cli --list-llm-models
.venv/bin/python -m autopsy.cli retool.com razorpay.com --fresh --iterations 0
```

`--check` bypasses the response cache and makes one authenticated Company Identify request. It prints only normalized identity, never the API key. Headless investigations save the same dossiers as the UI and write reports to `data/reports/`. A partial investigation returns exit code 1 with completed evidence preserved.

`--diagnose-llm` makes discovery plus two tiny plain/structured probes without retries. `--check-committee` uses explicitly synthetic diagnostic inputs with the real provider; it never claims those inputs describe a real company. Neither is part of pytest. `--fresh` bypasses HTTP cache; `--iterations 0` deliberately disables web follow-up for a low-cost integration check. `--no-llm` is an explicit deterministic mode.

### Validation performed in this build

- **137 pytest tests executed and passed**, with mocked external network responses and synthetic companies in temporary directories. A complete AppTest journey performs mandate → discovery/watchlist → two-company investigation → guided terms → allocation → reactive scenario → applied outcomes → revised allocation → committee → exports → replay. It verifies ₹4 crore changes to ₹2 crore after an actual modeled downside change and restores the original decision. This is automated UI validation, separate from the live checks below.
- Live connected Crustdata Identify resolved `retool.com` to company `633593`. Actual enrichment returned documented identity, workforce, hiring, funding and people fields. A narrower enrichment request also returned complete selected fields.
- Actual connected Web Search and Web Fetch requests executed. One fetched page returned a “Page Unavailable” document despite transport success; blocked-page detection and a regression test were added.
- An explicitly labeled **cached real MCP validation snapshot** was normalized, scored, rendered in the dashboard, and exported locally. It is private ignored data, not a shipped demo fixture.
- **Direct Python HTTP validated:** fresh run `1cf447edf997` completed Retool and Razorpay through four uncached Identify/Enrich calls, with 350/417 observations and 55% scored coverage each. Web follow-up was explicitly disabled for that smoke run. Uncached two-result Company Search also succeeded for India with a pagination cursor. Search requires `metadata.updated_at`, while Enrich accepted `updated_at`; missing provider update dates remain unknown. The earlier single-company `7ba175e66d54` run was cached real data, not a fresh HTTP investigation.
- **Live Gemini generation validated:** `gemini-3.5-flash` succeeded for plain text, minimal structured JSON, the real research planner for both companies and all three committee roles. A private memo using real dossiers plus explicitly illustrative modeled terms completed all three actual Gemini passes, retained both deals as MORE DILIGENCE REQUIRED and allocated zero because company financials were absent. Earlier 404/503/timeouts remain documented. One transient 503 in the fresh research run recovered on a bounded retry. No alternative provider was used.
- Streamlit started and its local health endpoint returned **HTTP 200 / ok**. No browser connection was available, so browser visual inspection and video recording remain outstanding. AppTest checks executed. The UX redesign additionally generated a 10-page native PDF from the existing real Retool/Razorpay dossier memo, rendered every page, and inspected its contact sheet plus full-size executive, scenario and appendix pages. A synthetic long-name/multipage-table PDF was also rendered and inspected. See [UX QA](docs/UX_QA.md).

## What the product does

- CSV/pasted portfolio validation, canonical-ID deduplication before repeated enrichment and exact-first identity checks. Secondary name results must corroborate a primary domain or provider-documented alias, otherwise the UI requires explicit candidate comparison and revalidates the selected canonical ID/domain. `notion.so` remains unresolved in the executed check; Retool and Razorpay are the validated sample pair.
- Collects actual Crustdata identity, headcount history, job-opening history, funding milestones, leadership profiles and provider news.
- Calculates comparable dated workforce/hiring trends and uses their severity and evidence gaps to choose follow-up search topics.
- Searches business or leadership developments, then fetches up to two readable, non-redirect source pages per iteration. Search snippets remain unverified leads. Blocked pages remain unknown.
- Optional Gemini proposes hypotheses, benign alternatives, permitted research focus and founder questions. Pydantic validates its structure; unsupported evidence IDs reject the entire plan. No model-generated assertion becomes a verified fact.
- Preserves raw values, source/API references, separate observation/event/publication/provider-update/retrieval dates, per-record live/cache provenance, verification status, conflicts and limitations.
- Generates intervention steps, founder questions, a draft email, an HTML briefing, Markdown report, and machine-readable evidence ledger. **No email is sent.**
- Persists after every stage, preserving completed company work across failures and interruptions.

## Assessment method

These are **investigation-priority heuristics, not validated probabilities of failure or bankruptcy**.

| Category | Weight | Current implementation |
|---|---:|---|
| Workforce | 35% | Dated provider employee-count series |
| Leadership | 30% | Profile observations and targeted research; no automatic departure score |
| Hiring | 20% | Dated provider open-job-count series |
| Business developments | 15% | Funding records and fetched research; no automatic adverse-event score |

Weights are configurable through `assess(evidence, weights=...)`, must cover all four categories and sum to 1.

For workforce and hiring:

1. Use non-conflicting, nonnegative counts from the same provider metric definition.
2. Latest observation must not be future dated or older than 120 days.
3. Choose a positive baseline closest to 90 days earlier, within a 60–120 day window.
4. `change_pct = (latest - baseline) / baseline * 100`.
5. Category severity is `clamp(-change_pct / threshold * 100, 0, 100)`. Threshold: 30% workforce contraction; 50% hiring contraction.
6. Coverage equals the sum of supported category weights. A score requires **at least 50% coverage and two comparable categories**; otherwise it is absent, not zero.
7. Priority is the weighted severity **normalized over supported categories**. ≥70 urgent review; ≥35 focused review; below 35 routine review of observed categories. Missing categories remain explicitly unresolved.

A low score never establishes safety. Hiring reductions may reflect roles filled, seasonality, efficiency, or coverage changes. Funding silence never proves a cash shortage. Source text and current leadership profiles do not establish departures without dated investigation. The numeric engine intentionally excludes unverified leadership/business events in this MVP.

Runway is unavailable without supplied financial inputs. Zero net burn has no finite depletion runway; negative net burn is unsupported by this simple calculator and is rejected. Revenue falling to zero is −100% growth, not unknown. The legacy calculator remains local to its view. VCOS labels financials as USER-PROVIDED DATA, MODELED ASSUMPTIONS or SYNTHETIC DEMO DATA and includes them in explicit snapshots/reports. Financial calculations do not become externally verified company evidence.

Execution is **COMPLETED** when required work finishes, **PARTIAL** for useful but incomplete work, **FAILED** when no useful result is produced. Coverage, single-source verification status, model generation and investment readiness are separate. Original histories retain their recorded statuses; old Gemini-only partial runs are not silently rewritten.

## API integration and reliability

Runtime calls `https://api.crustdata.com` with `Authorization: Bearer …` and `x-api-version: 2025-11-01`.

| Endpoint | Payload used | Purpose |
|---|---|---|
| `POST /company/identify` | `domains` or `names` | Canonical company resolution |
| `POST /company/search` | verified `filters`, selected `fields`, stable `sorts`, bounded `limit`, optional `cursor` | Indexed company discovery |
| `POST /company/enrich` | `crustdata_company_ids`, explicit `fields` | Company and workforce/hiring histories, funding, leadership, news |
| `POST /web/search/live` | `query`, `sources: [web, news]` | Evidence-dependent follow-up |
| `POST /web/enrich/live` | `urls` (up to two here) | Source document retrieval |

Verified documentation: [Identify](https://docs.crustdata.com/company-docs/identify/introduction), [Enrich](https://docs.crustdata.com/company-docs/enrichment/reference), [Web Search](https://docs.crustdata.com/web-docs/search/reference), [Fetch](https://docs.crustdata.com/web-docs/fetch/introduction), [pricing](https://docs.crustdata.com/general/pricing). Gemini uses [model discovery](https://ai.google.dev/api/models) and [generateContent](https://ai.google.dev/api/generate-content); runtime discovers a supported text Flash model or validates `GEMINI_MODEL` before generation.

Gemini uses httpx REST, not the Google GenAI SDK. Automatic discovery prefers the live-verified `gemini-3.5-flash`; an explicit `GEMINI_MODEL` remains authoritative. Shared research/committee transport uses a 5-second connect/25-second request timeout, 2,048 output-token ceiling and low thinking for supported models. At most two generation attempts per pass: one retry for transient 503, or one advertised alternate after 404 when no explicit model was selected. Authentication, quota and invalid output open a circuit. Role outputs are hypotheses only; facts come from the original ledger. Provider/model/status, safe error details and validation failures are visible. Never assume model listing guarantees generation access.

- One sequential HTTP client: conservative endpoint spacing (30 requests/minute for company calls, 10/minute for web calls), three maximum attempts, bounded backoff and 45-second HTTP timeouts.
- Explicit handling of 400, 401, 402, 403, 404, 429, server failures, transport failures and invalid JSON. Authentication/credit exhaustion halts further uncached calls. Permission failures remain visible.
- `MAX_API_CALLS` counts attempts including retries. `MAX_ITERATIONS` limits follow-up searches per company (hard maximum 4), each followed by at most one fetch call containing at most two pages.
- `MAX_CREDITS` is a **conservative estimated ceiling, not a guaranteed billing cap**. Identify reserves 0, enrichment 5, search 1, fetch 1/page. Account-specific field prices can differ. Actual `X-Credits-Used` is tracked when supplied and can stop later calls. A request can exceed its estimate; use your provider account controls for a hard monetary limit.
- Default 20 API attempts, 30 estimated credits, 2 research iterations/company. Up to five companies may exhaust these defaults and yield a useful partial report. Increase limits in the sidebar if appropriate.
- Query/payload response caching with original retrieval timestamps and 24-hour default TTL. HTTP caches contain real responses only. No fixtures are substituted into investigations.
- Run mode distinguishes LIVE DATA, CACHED REAL DATA, and mixed use. Tests use synthetic records in temporary directories; no synthetic demo button is exposed.
- Atomic run snapshots save after each stage. An interrupted run is marked visibly on reopening; a new run reuses eligible cached responses. There is no automatic process restart/resume worker.
- Single-provider observations are not independently verified. Duplicate URLs/records are deduplicated; matching text or different hostnames do not prove independence. Conflicting dated counts retain both values and are excluded from scoring. This MVP does not automatically infer semantic contradictions across articles.

## Architecture and repository

See [architecture and diagram](docs/ARCHITECTURE.md), [demo script](docs/DEMO.md), [submission checklist](docs/SUBMISSION.md), and [engineering rules](AGENTS.md).

```text
app.py                    Streamlit product interface
 autopsy/config.py        Environment and run limits
 autopsy/models.py        Pydantic evidence, signal, dossier, run schemas
 autopsy/ingestion.py     CSV and text normalization
 autopsy/api.py           Crustdata HTTP client and company resolution
 autopsy/research.py      Company, workforce, hiring, leadership and web collectors
 autopsy/evidence.py      Normalization, provenance, references and conflicts
 autopsy/risk.py          Deterministic dated trend assessment and runway safeguards
 autopsy/llm.py           Optional structured Gemini planner with fallback
 autopsy/diagnostics.py   Bounded credential-safe plain/structured provider probes
 autopsy/identity.py      Exact-first lookup and explicit candidate disambiguation
 autopsy/health.py        Independent execution/coverage/verification/freshness summaries
 autopsy/orchestrator.py  Bounded research decisions and action plans
 autopsy/reports.py       HTML, Markdown and JSON exports
 autopsy/briefing.html    Autoescaped standalone HTML report template
 autopsy/storage.py       Atomic JSON runs and timestamped response cache
 autopsy/cli.py           Live authentication check and headless investigations
 autopsy/mandate.py       Reviewed constraints, local mandates/watchlists/snapshots
 autopsy/discovery.py     Bounded documented indexed Company Search
 autopsy/finance.py       Supplied financials, readiness, cash and equity math
 autopsy/portfolio.py     Constrained scenario allocation and new-allocation stress
 autopsy/committee.py     Validated role perspectives and actual state differences
 autopsy/vcos_ui.py       Seven-section decision workspace and guided editors
 autopsy/vcos_reports.py  Investment committee HTML / Markdown / JSON memos
 tests/                   Mocked API, scoring, evidence, workflow, report and UI tests
 data/                    Private local cache, runs and reports (gitignored)
```

## Test and contribute

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app.py autopsy
.venv/bin/pip check
git diff --check
```

GitHub Actions runs pytest on Python 3.11 and 3.13. External calls are mocked in CI; do not add API secrets to tests. Local data may contain licensed provider records and private financial information: do not publish `data/`, `.env`, or private exports. Streamlit is configured for a local workstation; authentication, tenant isolation, shared quotas and deployment security are outside this hackathon MVP.

## Remaining submission gates and model boundaries

1. Perform browser visual review and record/upload the two-minute demo; no connected browser was available during implementation. Precise recording steps and narration are in [DEMO.md](docs/DEMO.md). Confirm the official deadline from the handbook; this repository does not invent a deadline or claim a submitted video.
2. Recheck provider status before presenting. Live Gemini is validated, but transient overload can still produce a visible deterministic fallback.
3. Supply real company-owned financial inputs and terms before presenting an actionable allocation. External company enrichment does not establish valuation or solvency.
4. Advanced SAFE/note/preferred conversion and liquidation waterfalls, multi-round cap tables, automated financial-document extraction, semantic contradiction verification and stress outcomes for existing holdings are not implemented. Existing holdings do affect all concentration constraints; current stress testing covers new allocations. Cap-table math models one ordinary-equity round with an explicit post-round pool convention.
5. Revenue sensitivity assumes changes pass fully through to cash flow against current net burn. Cash exhaustion is absorbing and implies zero recovery; cash paths stop at exhaustion. Exit proceeds exclude preferences, taxes and fees. These assumptions are inspectable beside outputs.
6. Natural-language thesis extraction is a conservative deterministic fallback for common INR/risk/horizon/exposure/reserve phrases. All omitted goals stay in the original thesis for manual review; constraints are never silently generated as facts. No claim of a successful live LLM thesis parser is made.

### Company intelligence comparison

Deal Comparison resolves selected canonical IDs across saved completed investigations, with the selected evidence context taking precedence. Frozen decision replay retains its original dossiers. The selected companies drive both the intelligence table and deal cards; additional candidates do not suppress investigated pairs. The table includes dated workforce/hiring changes, EWMA, OLS slopes, volatility, MAD alerts, historical funding and investors. Revenue, valuation and traffic remain unknown where absent. Short-term OLS extrapolation requires eight observations spanning 180 days and a latest observation within 120 days; it is an illustrative 30-day trend estimate without a validated prediction interval. Sparse data explicitly suppresses forecasting. The existing investigation-priority score and portfolio math remain separate from these operating statistics.

Local acceptance test `tests/test_real_comparison.py` uses private saved Retool/WhatsApp evidence in an isolated temporary workspace. It verifies an unrelated sidebar context, a third candidate, selection of the actual pair, −1.9%/+7.8% three-month workforce changes, 8.33% modeled ownership and generated PDF content. CI skips this private-data check when the saved investigation is absent; synthetic workflow and calculation tests still run.
