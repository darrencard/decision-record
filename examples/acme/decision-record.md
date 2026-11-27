# Decisions on quote drafting

Read 2026-11-26 · Decision record 0.3.5 · Illustrative

**All five decisions are made; none is open. Two took longer than usual to decide.**

5 decided, 0 open. 2 took longer than the usual 14 days to decide: D-0004 (28 days), D-0005 (21 days).

## What to do next

Review all five decisions against their success signals. Decides: Head of Product, Quoting squad. When: was due 2026-11-15.

## Days to decide

| Decision | Days · PLAN 14 DAYS | Decided by or waiting on |
|---|---|---|
| Build quote drafting now, against its landing brief | **7 DAYS** | Head of Product, Quoting squad |
| Quote drafts wait for the tradesperson's approval before they send | **14 DAYS** | Head of Product, Quoting squad |
| Prices come from the price book, never the model | **5 DAYS** | Tech lead, Quoting squad |
| Set when to undo quote drafting | **28 DAYS**, 14 over plan | Head of Product, Quoting squad |
| Choose the AI model for quote drafts | **21 DAYS**, 7 over plan | Tech lead, Quoting squad |

## Who made each call

- D-0001 Build quote drafting now, against its landing brief. Chosen: Build quote drafting now. Head of Product, Quoting squad decided on 2026-07-27, 7 days after it was opened. Owner Lead, Quoting squad, review by 2026-11-15.
  Can be undone: yes. Success signal: Quote draft acceptance rate at 40% or higher by 2026-11-15, as the landing brief sets.
  Assumes: Tradespeople accept a draft they can edit
  Assumes: AI usage of 9,000 per task is enough for a full quote
- D-0002 Quote drafts wait for the tradesperson's approval before they send. Chosen: Approve before send. Head of Product, Quoting squad decided on 2026-07-27, 14 days after it was opened. Owner Lead, Quoting squad, review by 2026-11-15.
  Can be undone: yes. Success signal: Wrong-line-item complaints below 5 a month by 2026-11-15 (illustrative).
  Assumes: Most wrong line items are caught when the tradesperson reads the draft
- D-0003 Prices come from the price book, never the model. Chosen: Prices from the price book. Tech lead, Quoting squad decided on 2026-07-27, 5 days after it was opened. Owner Lead, Quoting squad, review by 2026-11-15.
  Can be undone: yes. Success signal: No sent quote carries a price that differs from the price book, checked weekly to 2026-11-15 (illustrative).
- D-0004 Set when to undo quote drafting. Chosen: Undo when wrong-price quotes pass 2%. Head of Product, Quoting squad decided on 2026-08-10, 28 days after it was opened, longer than the usual 14. Owner Tech lead, Quoting squad, review by 2026-11-15.
  Can be undone: yes. Success signal: Wrong-price quotes stay below 2% to 2026-11-15 (illustrative).
- D-0005 Choose the AI model for quote drafts. Chosen: The mid-size model. Tech lead, Quoting squad decided on 2026-08-10, 21 days after it was opened, longer than the usual 14. Owner Tech lead, Quoting squad, review by 2026-11-15.
  Can be undone: yes. Success signal: AI usage per task within the landing brief's 9,000 budget to 2026-11-15 (illustrative).

## What this read

- Target: Quote draft acceptance rate, 40% or higher by 2026-11-15. Tested by D-0001.
- Portfolio review of 2026-07-27: rank 4 of 8; readiness 14 of 14 points.

## Evidence

| Figure | Value | Window |
|---|---|---|
| Open | 0 decisions | 2026-07-13 to 2026-11-26 |
| Decided | 5 decisions | 2026-07-13 to 2026-11-26 |
| Waiting longer than usual | 0 decisions | 2026-07-13 to 2026-11-26 |
| Past their decide-by date | 0 decisions | 2026-07-13 to 2026-11-26 |
| Waiting on nobody | 0 decisions | 2026-07-13 to 2026-11-26 |
| Usual time to decide (median) | 14 days | 2026-07-13 to 2026-11-26 |
| Days to decide, D-0001 | 7 days | 2026-07-20 to 2026-07-27 |
| Days to decide, D-0002 | 14 days | 2026-07-13 to 2026-07-27 |
| Days to decide, D-0003 | 5 days | 2026-07-22 to 2026-07-27 |
| Days to decide, D-0004 | 28 days | 2026-07-13 to 2026-08-10 |
| Days to decide, D-0005 | 21 days | 2026-07-20 to 2026-08-10 |

## For your engineers

Skill: decision-record 0.3.5.

Each decider's words, checked word for word against the source:

- D-0001: "My call: we build quote drafting now, against the brief as written, and we review it on 15 November." (Acme decide call, 2026-07-27 (illustrative))
- D-0002: "Decided: every drafted quote waits for the tradesperson to approve it before it sends." (Acme decide call, 2026-07-27 (illustrative))
- D-0003: "Prices come from the price book in fixed code. That is my call for v1." (Acme decide call, 2026-07-27 (illustrative))
- D-0004: "My call: we roll back quote drafting when wrong-price quotes pass 2%." (Acme spec review call, 2026-08-10 (illustrative))
- D-0005: "vendor-a/m drafts quotes in v1. Long drafts go to vendor-a/xl. That is my call." (Acme spec review call, 2026-08-10 (illustrative))

| Key name | Source |
|---|---|
| open | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d) |
| decided | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d) |
| waiting_long | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d) |
| past_due | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); open with a decide-by date before as_of |
| waiting_on_nobody | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d) |
| usual_days_to_decide | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); median days from opened to decided |
| days_to_decide@D-0001 | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0002 | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0003 | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0004 | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |
| days_to_decide@D-0005 | decision-record 0.3.5: counted from decisions.md (sha256 096127d5d48d); decided date minus the opened date |

Log: decisions.md, sha256 096127d5d48d. Model ids as written: vendor-a/m is the mid-size model, vendor-a/xl the large model.
