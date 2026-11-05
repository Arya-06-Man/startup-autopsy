# Startup Autopsy VCOS
### Autonomous Venture Capital Intelligence & Decision Platform

**Discover → Investigate → Verify → Compare → Stress-test → Allocate → Challenge → Decide → Report**

Startup Autopsy replaces substantial first-pass VC analyst work: company discovery, evidence investigation, mandate screening, deal comparison, scenario calculations, conditional capital allocation, structured committee challenge, decision replay and investment memo preparation. It extends the existing bounded investigator and evidence ledger; it never executes investments or sends outreach.

Built for **ContextCon 04, IIT Kanpur · Investing · Services, Replaced**.

## Use the decision workspace

1. **Overview:** describe your thesis, apply guided mandate edits, review every constraint and save. All fields—including existing holdings, ownership targets and custom rejection criteria—are editable in the advanced JSON view. Mandates persist locally.
2. **Discover:** search Crustdata by documented industry, country, funding round, headcount and growth filters. Sort/search each page, page with a stable cursor, save named watchlists and shortlist 2–5 companies. Explicitly launch the existing bounded investigation below the search results. Search does not deeply enrich all companies.
3. **Evaluate:** select companies from an investigation or enter domains for a terms-only comparison. Use the guided editor to supply terms and dated financial inputs. Unknowns remain blank. Financials are user-provided, not sourced or inferred by AI. A term-sheet, cap-table or financial-statement label is an attestation, not automatic document verification.
4. **Portfolio Lab:** compute constrained allocations and alternative scenario objectives. The optimizer may invest in neither. Missing approval-critical evidence, incompatible instruments and mandate violations exclude a deal. Existing holdings aggregate at cost. Reserve and liquidity capital remain separate.
5. **War Room:** compare cash paths, financing delays, exit values, ownership, MOIC and simplified annualized returns over 1/3/5/7/10 years. Model a single ordinary-equity financing round and follow-on requirement. Save and reopen scenarios.
6. **Investment Committee:** challenge the thesis with three structured roles from one provider, or explicitly labeled deterministic checklists when Gemini is unavailable. Export HTML, Markdown and JSON memos and save decision snapshots. Replay uses actual prior inputs and frozen evidence, with structural before/after differences.
7. **Evidence & Reports:** retain the original dossiers, six detailed investigation views, source ledger, history and research report exports. Observation, publication and retrieval dates are distinct; absent dates remain unknown.

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

Open **http://127.0.0.1:8501**. Start in Overview with your mandate. Discover accepts live search or up to five names/domains for investigation, including [samples/portfolio.csv](samples/portfolio.csv). Prefer primary domains to avoid ambiguous names. The investigation button requires an API key. Previous real runs remain available in Evidence & Reports.

`requirements.txt` supports compatible installations across Python versions. `requirements-lock.txt` records the exact environment tested here; its transitive pins may require Python 3.13 and are not the default installation path.

## Validate the real integration

```bash
.venv/bin/python -m autopsy.cli --check retool.com
.venv/bin/python -m autopsy.cli --check-discovery IND
.venv/bin/python -m autopsy.cli --check-llm
.venv/bin/python -m autopsy.cli --list-llm-models
.venv/bin/python -m autopsy.cli retool.com notion.so
```

`--check` bypasses the response cache and makes one authenticated Company Identify request. It prints only normalized identity, never the API key. Headless investigations save the same dossiers as the UI and write reports to `data/reports/`. A partial investigation returns exit code 1 with completed evidence preserved.

### Validation performed in this build

- **89 pytest tests executed and passed**, using mocked external network responses. Tests cover mandate validation/persistence, deterministic financial math, financing delays, impossible allocations, duplicate exposure, missing assumptions, zero deployment, reference rejection, escaping, replay, all seven routes, actual allocation/scenario UI actions and memo downloads.
- Live connected Crustdata Identify resolved `retool.com` to company `633593`. Actual enrichment returned documented identity, workforce, hiring, funding and people fields. A narrower enrichment request also returned complete selected fields.
- Actual connected Web Search and Web Fetch requests executed. One fetched page returned a “Page Unavailable” document despite transport success; blocked-page detection and a regression test were added.
- An explicitly labeled **cached real MCP validation snapshot** was normalized, scored, rendered in the dashboard, and exported locally. It is private ignored data, not a shipped demo fixture.
- **Direct Python HTTP validated:** uncached Identify succeeded; a real bounded Retool investigation completed with saved local reports and 55% scored evidence coverage. An uncached two-result Company Search succeeded for India, including a pagination cursor. A rejected projection was corrected using the provider's filterable/returnable field distinction. See [baseline audit](docs/BASELINE_AUDIT.md).
- **Live Gemini generation remains unvalidated:** configured credentials successfully discovered models, but actual structured requests encountered HTTP 404/503 and timeouts, including the stable alias. Diagnostics preserve this limitation. Mocked structured planner and committee passes validate schemas and reject unsupported IDs. Fallback is never labeled Gemini success.
- Streamlit started and its local health endpoint returned **HTTP 200 / ok**. No browser connection was available, so visual inspection and video recording remain outstanding. AppTest checks executed.

## What the product does

- CSV/pasted portfolio validation, deduplication and exact-domain identity checks; ambiguous results request a specific domain rather than guessing.
- Collects actual Crustdata identity, headcount history, job-opening history, funding milestones, leadership profiles and provider news.
- Calculates comparable dated workforce/hiring trends and uses their severity and evidence gaps to choose follow-up search topics.
- Searches business or leadership developments, then fetches up to two readable, non-redirect source pages per iteration. Search snippets remain unverified leads. Blocked pages remain unknown.
- Optional Gemini proposes hypotheses, benign alternatives, permitted research focus and founder questions. Pydantic validates its structure; unsupported evidence IDs reject the entire plan. No model-generated assertion becomes a verified fact.
- Preserves raw values, original source/API record references, event/publication/retrieval dates, verification status, conflicts and limitations.
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

Runway is unavailable without supplied financial inputs. The legacy calculator remains local to its view. VCOS accepts dated user financials, labels them unverified, and includes supplied assumptions in committee reports and explicitly saved decision/scenario snapshots. Financial calculations do not become externally verified company evidence.

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

1. Obtain a successful live Gemini structured response before claiming AI committee validation; current failures remain visible.
2. Perform browser visual review and record the two-minute demo; no connected browser was available during this implementation.
3. Supply real company-owned financial inputs and terms before presenting an actionable allocation. External company enrichment does not establish valuation or solvency.
4. Advanced SAFE/note/preferred conversion and liquidation waterfalls, multi-round cap tables, automated financial-document extraction, semantic contradiction verification and stress outcomes for existing holdings are not implemented. Existing holdings do affect all concentration constraints; current stress testing covers new allocations. Cap-table math models one ordinary-equity round with an explicit post-round pool convention.
5. Revenue sensitivity assumes changes pass fully through to cash flow against current net burn. Cash exhaustion is absorbing and implies zero recovery; cash paths stop at exhaustion. Exit proceeds exclude preferences, taxes and fees. These assumptions are inspectable beside outputs.
6. Natural-language thesis extraction is a conservative deterministic fallback for common INR/risk/horizon/exposure/reserve phrases. All omitted goals stay in the original thesis for manual review; constraints are never silently generated as facts. No claim of a successful live LLM thesis parser is made.
