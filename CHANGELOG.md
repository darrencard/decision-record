# Changelog

## 0.3.0, 2026-11-26

- Step 01 (Decide) of the Landing Loop. `open_decisions.py --loop FOLDER --bet SLUG` reads the bet's landing brief (through the Leader Report's parser, vendored byte-identical) and the `portfolio` key, and writes only the `decisions` key of `landing/<bet>.json`. Every other key is kept as found. Every figure carries value, unit, source, window and as_of.
- The key's `rows` are the Leader Report's decision format, so its decision slide reads them unchanged. `brief.tested_by` names the decided record whose success signal is the brief's bar.
- A brief edited after the record opened, an incomplete brief, or an invalid log is refused, and nothing is written.
- `--html` and `--md`: one self-contained page in the Leader Report style, with its Markdown twin. Brass marks who decides, who a call waits on, and the deadline. No status colour.
- Sample: `python3 examples/acme/sample.py` rebuilds Acme's decide call of 2026-07-27 into the log, the record key and the page. A test checks it reproduces the committed files byte for byte.
- `from_thread.py`: Slack and Linear exports first, CSV as the fallback, into a source the checks read. No Leader Report collector reads thread text, so this one is new.
- Outcome words are now worked, pending and missed. Landed, watch and stalled are a bet's status, and only did-it-land sets them. Logs written before 0.3.0 read as the new words.
- Python 3.11 or later, like the rest of the loop.
- Past due means a passed decide-by date and nothing else. A call that has waited longer than the log's usual time to decide is "waiting longer than usual", a new `waiting_long` flag, count and figure. Escalation follows the long wait, as before.
- The Acme story holds across the loop: the sample records the rollback trigger (D-0004) and model tier (D-0005) from the spec review call of 2026-08-10, and the record key and page read the full log as of 2026-11-26 (5 decided, 0 open), with each call's days to decide against the usual. decision-record reads only the brief and portfolio, so a later as_of keeps record order. The log as it stood on 2026-07-27 is kept in `decide-step/` and read with no record write. The page lede names the calls that took longer than usual.
- `record.py decide --source-name` cites where the call was made. `decide` rewrites the log through a temp file. Every entry script checks for Python 3.11 before it reads or writes anything. The page sets selection and the focus ring to ink, not the template's green.
- The decider rule is explicit: one person's name, or one role scoped to one team, written "<role>, <team or squad>" ("Head of Product, Quoting squad"). A bare role, a group, or a role with its team in front and no comma ("Quoting squad lead") fails, however it is capitalised. The Acme sample uses scoped roles.

## 0.2.0, 2026-11-26

- `open_decisions.py --leader-report FILE` writes open decisions in the Product & Technology Leader Report's decision format (ask, options, recommendation, deadline, plus owner, days waiting, id and source), as Markdown or CSV. The report's decision slide reads it unchanged. A test round-trips it through the report's own intake, draft and validate scripts.
- New record fields: `Decide by` (the deadline) and `Recommendation` (who recommends what, from the source). A passed decide-by date warns.
- The export refuses an option holding the word "or", which the slide would split in two.

## 0.1.0, 2026-11-26

- First version: decision records from a thread, notes or a transcript; named-decider, evidence and date checks; success signal and assumptions; open decisions with days waiting and on whom; follow-through; ADR export.
