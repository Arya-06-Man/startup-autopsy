# Two-minute VCOS demonstration

This is a ready-to-read script and recording procedure. No video or browser visual review was performed by the agent: the browser connection was unavailable. The repository is public; the submitting team must verify the official deadline and upload the actual video.

## Prepare before recording

1. Start `.venv/bin/streamlit run app.py --server.address 127.0.0.1 --server.port 8501` and open http://127.0.0.1:8501.
2. Check provider access once: `--check retool.com`, `--check-discovery IND`, and `--check-llm` via `.venv/bin/python -m autopsy.cli`. These make actual calls; do not loop diagnostics. Gemini `gemini-3.5-flash` and the Retool/Razorpay pair were validated during final QA.
3. Keep the completed two-company investigation selected in the sidebar. Reopening its saved dossier is an archived real investigation, not a fresh live call. Show the actual retrieval time and mode. Leave Refresh off for the recording unless you intend to spend credits on a fresh investigation.
4. Prepare an open-sector/open-geography mandate: INR 100,000,000 total capital, Moderate risk, five years, 30% reserve, 25% company limit, 50% sector limit. That leaves INR 70,000,000 before existing holdings and liquidity. Narrower preferences may legitimately exclude a company.
5. For each company, illustrative ordinary-equity terms may use INR 20,000,000 proposed cheque, INR 80,000,000 pre-money and INR 20,000,000 total round. Select **MODELED ASSUMPTIONS**. The implied ownership is 20%. These numbers are not either company's real valuation or funding terms. Leave company cash, revenue, financial date and document attestations missing unless real records were supplied.
6. The correct result with missing company financials is MORE DILIGENCE REQUIRED and no investment. Do not mark documents verified or invent financial statements to produce an allocation. The positive INR 40m → INR 20m allocation path is covered by the isolated synthetic AppTest, not claimed as a real-company investment recommendation.
7. Prepare a separate hypothetical War Room: cash INR 100m, monthly net burn INR 1m, five years, investor cost INR 20m, 20% ownership, exit assumptions downside INR 50m / base INR 200m / upside INR 500m. Clearly state these are hypothetical operating assumptions, not company cash balances. The base survives the horizon and has 2x MOIC. Increasing burn to INR 2m exhausts cash in month 50 and produces zero recovery under the stated model.
8. Run the committee before recording if you need a reliable two-minute presentation. Show its actual engine, model and result; generation can still encounter overload and must visibly fall back. A saved memo's recorded generation is not a new live response.

## Record precisely

- On macOS press Shift–Command–5, select the browser/window region, enable the microphone in Options and start recording. Use a readable desktop viewport around 1440 × 900; check text and tables visually first.
- Keep `.env`, terminal history, private financial files and unrelated tabs off-screen. Do not publish raw provider exports without checking licensing.
- Follow the script below; stop at or before 2:00. Preview the video with audio, confirm the playback link works without private-account permissions, then put that actual link in the submission form.
- Public repo: https://github.com/Arya-06-Man/startup-autopsy. Public architecture: https://github.com/Arya-06-Man/startup-autopsy/blob/main/docs/ARCHITECTURE.md. Confirm the handbook's deadline/timezone and submission destination manually; neither is guessed here.

## 0:00–0:20 — Mandate

“Startup Autopsy replaces the analyst workflow between company intelligence and an investment committee decision. Here is a ten-crore mandate with a thirty-percent follow-on reserve and hard exposure limits. Seven crore remains available before other holdings or liquidity needs.”

Show Overview, the reviewed constraints and Save reviewed mandate. Never silently loosen a limit to make a deal pass.

## 0:20–0:40 — Discovery and diligence

“Discovery queries Crustdata's actual index. The filters explain why each company appeared. We shortlist candidates instead of enriching every search result. Here are two completed real investigations with their original source dates.”

Show Discover, the real results table and Add selected to evaluation. Switch to the prepared Retool/Razorpay evidence context. Label archived/cached results accurately.

## 0:40–1:00 — Comparison

“These entry terms are illustrative modeled assumptions. Ordinary-equity ownership is calculated deterministically. Company financial statements remain unknown, so both deals require more diligence.”

Show Evaluate, the side-by-side table, 20% ownership where using the prepared example, source coverage, financial unknowns and deal breakers.

## 1:00–1:25 — Allocate and stress

“The allocator respects capital, reserves and concentration. It can keep all capital uninvested. In this hypothetical War Room, increasing burn changes the cash path immediately; financing after exhaustion does not rescue the modeled company.”

Show Portfolio Lab's actual no-investment explanation. In War Room change burn from INR 1m to INR 2m, show month-50 exhaustion, zero-recovery output and the updated assumptions. Applying outcomes to a deal requires matched mandate horizon, ownership and cost basis and an explicit confirmation; missing financial evidence still blocks approval.

## 1:25–1:45 — Challenge and replay

“One verified provider runs growth, skeptical-risk and portfolio-manager passes. These are cited AI hypotheses, not independent external experts. Changing an assumption invalidates old recommendations; replay shows the exact changed field and preserves the prior decision.”

Show the actual Gemini/fallback status, cited arguments and approval conditions. Save/reopen a prepared decision snapshot and show its real differences.

## 1:45–2:00 — Deliver

“The output is a decision memo with the mandate, terms, modeled outcomes, opposing arguments, evidence and missing diligence. No trade or founder outreach is executed.”

Download/open HTML, Markdown or JSON. Show the executive summary and source dates. State the current executed test count from README; final QA recorded 129 passing offline tests plus separate real-provider checks.

## Submission gate

Technical workflow: validated. Visual presentation review and actual video upload: pending human execution. A working application is not a claim that the competition submission or video has been completed.
