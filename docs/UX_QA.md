# Frontend redesign QA

## Scope and baseline

The starting main commit was `9a9081c`; the working tree was clean and synchronized with origin/main. Baseline: 129 tests passed. This change preserves Python + Streamlit, the existing Crustdata client, identity validation, bounded orchestrator, financial engine, optimizer, committee generation, source ledger, original investigation history and exports.

The principal UX defects were routing and presentation: the entry screen mixed setup with analysis, navigation followed technical settings, company lookup was buried, prerequisite screens lacked direct next actions, and report downloads lacked native PDF output. The change adds presentation helpers and a local document library rather than replacing backend services.

## Implemented and checked

- Default Investment Intelligence overview, explicit-submit global company search, four actionable feature cards, compact dismissible/persistent onboarding, mandate KPIs and real recent activity.
- Visible icon-labeled sidebar routes, settings collapsed below navigation, persistent company/comparison/mandate contexts.
- Company identity lookup through the original service, including required confirmation and canonical ID/domain revalidation for ambiguous matches. Search results persist; reruns do not repeat lookup calls.
- Search actions open a company, populate actual investigation inputs, save watchlists and save evaluation context. Discovery remains bounded and uses existing documented filters.
- Company dossiers and side-by-side deal cards preserve unknowns, provenance and source drill-down. Financial inputs remain supplied assumptions; no company metrics are invented.
- Portfolio budget/reserve/limit summaries, allocation explanations, alternative strategies and original exposure/stress charts.
- Left-side Operations/Financing/Returns controls and right-side live War Room outcomes. Original deterministic mathematics and snapshot/replay remain unchanged.
- Guided committee prerequisites, visibly labeled model/fallback status, preserved three-role review, validated saved reports and five report controls.
- Native A4 PDF from the same validated context as HTML/Markdown/JSON, embedded fonts, headers/footers/page numbers, source links, wrapping/repeated table headers and vector cash chart. Print downloads the actual PDF for normal viewer printing.

## Verification executed

- 137 pytest tests passed (129 preserved/adapted route expectations + 8 new UI/PDF tests).
- The existing complete investor journey still performs mandate → discovery/watchlist → investigation → terms → allocation → reactive scenario → revised allocation → committee → exports → replay with mocked network and synthetic companies.
- New interaction tests cover homepage navigation, guidance, saved mandate/guide preferences, empty reports/history/company pages, submitted search, no repeated calls on rerun, watchlist/view/investigate/compare actions, ambiguous identity confirmation, 429 display and all report download controls.
- Native PDF tests check validated ownership/calculations, rejected stale calculations, source URI annotations, A4 dimensions, missing data, long company names, multipage tables, repeated page numbering, text bounding boxes, conflicting records and escaped provider markup.
- A real PDF was produced locally from the existing verified Retool/Razorpay memo plus explicitly illustrative modeled terms. The PDF reused saved provider data; a separate explicit-refresh Company Search UI check successfully resolved Retool through the real Crustdata service with no UI exceptions or warnings. All 10 PDF pages were rendered; the full contact sheet and full-size executive, scenario and source-register pages were visually inspected. A separate synthetic long-name/multipage-table artifact was rendered and inspected. Both live-source inputs and PDFs remain private under ignored data/.
- The PDF register contains the 14 cited, identity and conflicting reference records; the companion JSON retains all 769 references. No original ledger records were removed.
- Python compilation, dependency consistency and Git whitespace checks executed. Streamlit health is checked before delivery.

## Limits

Browser setup returned `No browser is available`; the connected-browser listing was empty. Browser screenshots and responsive visual inspection were therefore unavailable. Streamlit interaction tests are executed, not a substitute claim of browser visual QA. No demo video was recorded.

PDFs use ordinary-equity scenario conventions already disclosed by the application. Unsupported font characters are explicitly represented as Unicode code points with a font-coverage note; original text remains in JSON. No screenshot PDF or browser screenshot is used.

Earlier live provider validations are preserved in FINAL_QA.md. This frontend milestone additionally verified the actual Company Search UI with an uncached Retool identity lookup (LIVE DATA, 2026-11-05T23:46:12Z), all four result actions present and no UI exceptions. No deep enrichment or new Gemini generation was requested. No confidential reports or credentials are included in Git.
