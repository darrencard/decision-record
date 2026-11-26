# Changelog

## 0.2.0 (2026-11-26)

- `open_decisions.py --leader-report FILE` writes open decisions in the Product & Technology Leader Report's decision format (ask, options, recommendation, deadline, plus owner, days waiting, id and source), as Markdown or CSV. The report's decision slide reads it unchanged. A test round-trips it through the report's own intake, draft and validate scripts.
- New record fields: `Decide by` (the deadline) and `Recommendation` (who recommends what, from the source). A passed decide-by date warns.
- The export refuses an option holding the word "or", which the slide would split in two.

## 0.1.0 (2026-11-26)

- First version: decision records from a thread, notes or a transcript; named-decider, evidence and date checks; success signal and assumptions; open decisions with days waiting and on whom; follow-through; ADR export.
