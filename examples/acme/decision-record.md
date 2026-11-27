# Decisions on quote drafting

Read 2026-11-26 · decision-record 0.3.0 · Illustrative

5 decided, 0 open. 2 took longer than the usual 14 days to decide: D-0004 (28 days), D-0005 (21 days).

Next step: No open decisions on this bet.

Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

## Open, as the Leader Report shows them

| ask | options | recommendation | deadline | owner | days_waiting | id | source |
|---|---|---|---|---|---|---|---|

## Decided

- D-0001 Build quote drafting now, against its landing brief. Chosen: Build quote drafting now. Head of Product, Quoting squad decided on 2026-07-27, 7 days after it was opened. Owner Lead, Quoting squad, review by 2026-11-15.
  Reversible: yes. Success signal: Quote draft acceptance rate at 40% or higher by 2026-11-15, as the landing brief sets.
  Assumes: Tradespeople accept a draft they can edit
  Assumes: 9,000 tokens per task is enough for a full quote
  In their words: "My call: we build quote drafting now, against the brief as written, and we review it on 15 November."
- D-0002 Quote drafts wait for the tradesperson's approval before they send. Chosen: Approve before send. Head of Product, Quoting squad decided on 2026-07-27, 14 days after it was opened. Owner Lead, Quoting squad, review by 2026-11-15.
  Reversible: yes. Success signal: Wrong-line-item complaints below 5 a month by 2026-11-15 (illustrative).
  Assumes: Most wrong line items are caught when the tradesperson reads the draft
  In their words: "Decided: every drafted quote waits for the tradesperson to approve it before it sends."
- D-0003 Prices come from the price book, never the model. Chosen: Prices from the price book. Tech lead, Quoting squad decided on 2026-07-27, 5 days after it was opened. Owner Lead, Quoting squad, review by 2026-11-15.
  Reversible: yes. Success signal: No sent quote carries a price that differs from the price book, checked weekly to 2026-11-15 (illustrative).
  In their words: "Prices come from the price book in fixed code. That is my call for v1."
- D-0004 Set the rollback trigger for quote drafting. Chosen: Roll back when wrong-price quotes pass 2%. Head of Product, Quoting squad decided on 2026-08-10, 28 days after it was opened, longer than the usual 14. Owner Tech lead, Quoting squad, review by 2026-11-15.
  Reversible: yes. Success signal: Wrong-price quotes stay below 2% to 2026-11-15 (illustrative).
  In their words: "My call: we roll back quote drafting when wrong-price quotes pass 2%."
- D-0005 Choose the model tier for quote drafts. Chosen: vendor-a/m. Tech lead, Quoting squad decided on 2026-08-10, 21 days after it was opened, longer than the usual 14. Owner Tech lead, Quoting squad, review by 2026-11-15.
  Reversible: yes. Success signal: Tokens per task within the brief's 9,000 budget to 2026-11-15 (illustrative).
  In their words: "vendor-a/m drafts quotes in v1. Long drafts go to vendor-a/xl. That is my call."

## What it read

- Brief: Quote draft acceptance rate, 40%, higher is better, by 2026-11-15. Tested by D-0001.
- Portfolio: bet-portfolio-review 0.3.1, as of 2026-07-27: rank 4 (rank of 8 bets, 1 needs work first); brief score 14 (points of 14).

## Ledger

| Figure | Value | Window | Source |
|---|---|---|---|
| open | 0 decisions | 2026-07-13 to 2026-11-26 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d) |
| decided | 5 decisions | 2026-07-13 to 2026-11-26 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d) |
| waiting_long | 0 decisions | 2026-07-13 to 2026-11-26 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d) |
| past_due | 0 decisions | 2026-07-13 to 2026-11-26 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); open with a decide-by date before as_of |
| waiting_on_nobody | 0 decisions | 2026-07-13 to 2026-11-26 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d) |
| usual_days_to_decide | 14 days | 2026-07-13 to 2026-11-26 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); median days from opened to decided |
| days_to_decide@D-0001 | 7 days | 2026-07-20 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0002 | 14 days | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0003 | 5 days | 2026-07-22 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0004 | 28 days | 2026-07-13 to 2026-08-10 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0005 | 21 days | 2026-07-20 to 2026-08-10 | decision-record 0.3.0: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
