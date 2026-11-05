# Five-minute demo

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
