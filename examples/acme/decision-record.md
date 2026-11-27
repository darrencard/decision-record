# Decisions on quote drafting

Read 2026-07-27 · decision-record 0.3.0 · Illustrative

3 decided, 2 open. 1 past due: D-0004 has waited 14 days on Tom Okafor, against a usual 7.

Next step: D-0004 waits on Tom Okafor: set the rollback trigger for quote drafting by 2026-08-03.

Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.

## Open, as the Leader Report shows them

| ask | options | recommendation | deadline | owner | days_waiting | id | source |
|---|---|---|---|---|---|---|---|
| Set the rollback trigger for quote drafting | Roll back when wrong-price quotes pass 2% or Roll back when rejected drafts pass 30% | Sam Whitfield recommends the wrong-price trigger at 2%. Waiting on Tom Okafor, 14 days open, past the usual 7 days to decide. | 2026-08-03 | Tom Okafor | 14 | D-0004 | Acme decide call, 2026-07-27 (illustrative) |
| Choose the model tier for quote drafts | vendor-a/xl or vendor-a/m | Tom Okafor recommends vendor-a/m, to stay inside the 9,000 token budget. Waiting on Priya Raman, 7 days open. | 2026-08-03 | Priya Raman | 7 | D-0005 | Acme decide call, 2026-07-27 (illustrative) |

## Decided

- D-0001 Build quote drafting now, against its landing brief. Chosen: Build quote drafting now. Maya Ortiz decided on 2026-07-27. Owner Tom Okafor, review by 2026-11-15.
  Reversible: yes. Success signal: Quote draft acceptance rate at 40% or higher by 2026-11-15, as the landing brief sets.
  Assumes: Tradespeople accept a draft they can edit
  Assumes: 9,000 tokens per task is enough for a full quote
  In their words: "My call: we build quote drafting now, against the brief as written, and we review it on 15 November."
- D-0002 Quote drafts wait for the tradesperson's approval before they send. Chosen: Approve before send. Maya Ortiz decided on 2026-07-27. Owner Tom Okafor, review by 2026-11-15.
  Reversible: yes. Success signal: Wrong-line-item complaints below 5 a month by 2026-11-15 (illustrative).
  Assumes: Most wrong line items are caught when the tradesperson reads the draft
  In their words: "Decided: every drafted quote waits for the tradesperson to approve it before it sends."
- D-0003 Prices come from the price book, never the model. Chosen: Prices from the price book. Priya Raman decided on 2026-07-27. Owner Tom Okafor, review by 2026-11-15.
  Reversible: yes. Success signal: No sent quote carries a price that differs from the price book, checked weekly to 2026-11-15 (illustrative).
  In their words: "Prices come from the price book in fixed code. That is my call for v1."

## What it read

- Brief: Quote draft acceptance rate, 40%, higher is better, by 2026-11-15. Tested by D-0001.
- Portfolio: bet-portfolio-review 0.3.0, as of 2026-07-27: rank 4 (rank of 8 bets, 1 needs work first); brief score 14 (points of 14).

## Ledger

| Figure | Value | Window | Source |
|---|---|---|---|
| open | 2 decisions | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887) |
| decided | 3 decisions | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887) |
| past_due | 1 decisions | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887) |
| waiting_on_nobody | 0 decisions | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887) |
| oldest_open | 14 days | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); as_of minus the opened date |
| usual_days_to_decide | 7 days | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); median days from opened to decided |
| days_waiting@D-0004 | 14 days | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); as_of minus the opened date |
| days_waiting@D-0005 | 7 days | 2026-07-20 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); as_of minus the opened date |
| days_to_decide@D-0001 | 7 days | 2026-07-20 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); decided date minus the opened date |
| days_to_decide@D-0002 | 14 days | 2026-07-13 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); decided date minus the opened date |
| days_to_decide@D-0003 | 5 days | 2026-07-22 to 2026-07-27 | decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887); decided date minus the opened date |
