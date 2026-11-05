# Two-minute VCOS demo

This is a recording script, not a claim that a video was recorded. Browser connection was unavailable during implementation.

## 0:00–0:20 — Investor mandate

“I have capital, constraints and competing deals. Startup Autopsy turns company intelligence into auditable investment work.” In Overview enter the ₹10 crore Indian B2B SaaS example, draft constraints, review the guided/advanced fields, and save. Show the explicit follow-on reserve and deployable capital.

## 0:20–0:40 — Discover and investigate

In Discover, search with `IND` plus an exact documented industry if needed. Explain why the companies match and why index observations are not investment recommendations. Select two domains and launch bounded diligence, or reopen a previously completed real investigation with its original retrieval date. Do not imply cached data is a new live call.

## 0:40–1:00 — Compare and question

In Evaluate select two investigated companies and enter **actual supplied** terms and dated financials with the guided editor. If no real financials are available, leave them missing and show “MORE DILIGENCE REQUIRED.” Never invent real-company valuations for presentation. Show ownership, valuation/revenue where supplied, source coverage and missing documents side by side.

## 1:00–1:20 — War Room and allocation

Use explicitly described user assumptions for cash, burn, funding timing and exit values. Run the scenario comparison, show delayed financing/capital loss and assumptions. In Portfolio Lab compute conditional allocations and alternatives. A zero-investment result is a valid decision; show which hard constraint or missing fact prevents deployment.

## 1:20–1:45 — Challenge and replay

Run committee challenge. State which engine actually responded; current live Gemini generation has not been validated, so show deterministic fallback honestly if it persists. Three AI role passes are one provider, not independent experts. Save a decision, change a supplied assumption, recompute and compare actual snapshot differences.

## 1:45–2:00 — Deliver the service

Download the HTML committee memo and JSON audit record. Open Evidence & Reports to show a finding's original evidence IDs and separate source dates. “No transaction, fabricated financial or founder outreach. The output is a reviewed work product with explicit approval conditions.” State the executed test count from README.

## Longer investigation walkthrough

## Before presenting

1. Create `.env` with a valid Crustdata key. Optionally add Gemini; never show the file or terminal history containing keys.
2. Run `.venv/bin/python -m autopsy.cli --check retool.com` to verify Python runtime credentials.
3. Start `.venv/bin/streamlit run app.py` and launch a single company investigation. Check endpoint access and credits before using a larger portfolio.
4. Keep the completed real run in the archive. Label it cached when reopened. Do not claim cached replay is a new live request.
5. Download the HTML briefing and JSON ledger. Review observations, dates, limitations and any failed fetches before presenting.

## 0:00 — The analyst service being replaced

“Portfolio monitoring means resolving companies, checking changing operating signals, investigating explanations, reconciling sources, and producing an investor follow-up. Startup Autopsy performs that workflow and saves the result.”

## 0:30 — Launch investigation

Paste one to three actual primary domains or upload `samples/portfolio.csv`. Show the budget controls and start the investigation. Explain each displayed stage as actual API work runs. A slow or failed source is visible; don't hide it.

## 1:30 — Explain the decisions

Open a company dossier. Show the decision trail: which observation or evidence gap caused the next research call. Explain that Gemini is optional and cannot invent tool results or alter deterministic scores. If no real anomaly exists, explain the coverage gap and resulting targeted research rather than inventing a finding.

## 2:15 — Inspect the evidence

Open a trend's exact evidence IDs in the timeline. Show event dates, retrieval dates, source/API references and original values. Contrast single-provider observations, unverified search leads, and fetched documents. State that none is automatically independently corroborated.

## 3:00 — Assess with restraint

Show the formula and observed-category coverage. Explain missing leadership/business data, alternate explanations, and why some companies are unscored. Hiring reductions do not establish financial distress; funding silence does not imply a cash shortage.

## 3:45 — Deliver the service

Open investor actions: urgency, evidence to request, founder questions and draft email. No email is sent. Download the HTML briefing and JSON evidence ledger to show a finished work product.

## 4:30 — Robustness and honest boundaries

Reopen an archived investigation. Explain partial results, API errors, budget stops, cached timestamps and LLM fallback. Mention the executed test count and remaining live integration/visual QA gates truthfully.

## If live calls are unavailable

Show a previously completed real run and its original retrieval timestamp. Say “cached real investigation,” explain the connection error, and show that existing results remain usable. If no real run exists, demonstrate input validation and the test results; do not relabel synthetic fixtures as company intelligence.
