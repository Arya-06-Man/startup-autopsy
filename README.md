# STARTUP AUTOPSY
### Autonomous VC Portfolio Intelligence & Intervention Agent

**Detect → Investigate → Verify → Assess → Recommend → Report**

Startup Autopsy replaces the first pass of portfolio monitoring: intake, company identity resolution, collection of workforce/hiring/funding/leadership records, evidence-dependent research, source review, priority assessment, and a finished investor follow-up briefing.

Built for **ContextCon 04, IIT Kanpur · Investing · Services, Replaced**.

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

Open **http://127.0.0.1:8501**. Enter up to five names/domains, or upload [samples/portfolio.csv](samples/portfolio.csv). Prefer primary domains to avoid ambiguous names. The launch button requires an API key. Reopen previous investigations from the archive, inspect dossiers and source records, and download HTML, Markdown, or JSON.

`requirements.txt` supports compatible installations across Python versions. `requirements-lock.txt` records the exact environment tested here; its transitive pins may require Python 3.13 and are not the default installation path.

## Validate the real integration

```bash
.venv/bin/python -m autopsy.cli --check retool.com
.venv/bin/python -m autopsy.cli retool.com notion.so
```

`--check` bypasses the response cache and makes one authenticated Company Identify request. It prints only normalized identity, never the API key. Headless investigations save the same dossiers as the UI and write reports to `data/reports/`. A partial investigation returns exit code 1 with completed evidence preserved.

### Validation performed in this build

- **45 pytest tests executed and passed**, using mocked external network responses. UI tests cover empty and populated dashboards, all six sections, and downloadable reports.
- Live connected Crustdata Identify resolved `retool.com` to company `633593`. Actual enrichment returned documented identity, workforce, hiring, funding and people fields. A narrower enrichment request also returned complete selected fields.
- Actual connected Web Search and Web Fetch requests executed. One fetched page returned a “Page Unavailable” document despite transport success; blocked-page detection and a regression test were added.
- An explicitly labeled **cached real MCP validation snapshot** was normalized, scored, rendered in the dashboard, and exported locally. It is private ignored data, not a shipped demo fixture.
- **Direct Python HTTP live investigation is not yet validated:** this workspace had no `CRUSTDATA_API_KEY` in `.env` or its environment. Running `--check` produced the expected actionable missing-key error.
- **Live Gemini is unvalidated:** no Gemini key was available. Model discovery, malformed output, unsupported evidence references and fallback are tested with mocks.
- The local Streamlit server started successfully. Browser visual inspection was unavailable because no browser connection was exposed; Streamlit AppTest checks executed.

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

Runway is unavailable by default. The optional calculator accepts user-supplied cash, positive monthly net burn and a non-future financial as-of date; computes `cash / monthly burn`; labels the inputs unverified; and does not persist or insert this calculation into the evidence report.

## API integration and reliability

Runtime calls `https://api.crustdata.com` with `Authorization: Bearer …` and `x-api-version: 2025-11-01`.

| Endpoint | Payload used | Purpose |
|---|---|---|
| `POST /company/identify` | `domains` or `names` | Canonical company resolution |
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

## Remaining submission gates

1. Add a valid local Crustdata key, execute `--check` and a direct Python investigation, inspect the resulting report.
2. Optionally configure Gemini and verify an actual compatible model response.
3. Perform browser visual review and record the demo.
4. Review the explicit limitations above before presenting scored coverage or source verification.
