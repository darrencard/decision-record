# Changelog

## 0.3.1, 2026-11-27

- The HTML page follows the Landing Loop sample anatomy, built like did-it-land's and eval-kit's: the shared header (mark, DACARD, skill, date, version, blue Illustrative tag), the verdict as the heading ("All five decisions are made; none is open. Two took longer than usual to decide."), the signature picture, one next step with its person in brass and when it is due, then each call in two columns and what the record read. The evidence ledger and an engineers' fold (key names, sources, the log's hash, model ids) are folded, and so is each decider's exact wording. No call to action: the page is the skill's own output.
- The signature picture: one timeline row per decision, from the day it was raised (open circle) to the day a named person made it (a brass figure). Rows that took longer than the log's usual time are drawn heavy and tagged "Longer than usual"; open calls are dashed. A 640 wide variant beside the next step on desktop and a 340 wide one for phones; its aria-label states the answer. Drawn with svgkit, vendored byte-identical from landing-loop 5d01756 and pinned in `VENDORED.json` under `landing-loop`.
- With nothing open, the next step is the next review: "Review all five decisions against their success signals", for the person the landing brief names, with the review date.
- Plain words in the page and the Markdown twin: project, target, when to undo it, the mid-size and large model, AI usage per task, can be undone. The log, the record key and each decider's quoted words are unchanged apart from `tool`.
- Design fix round 2: no text below 11px at any width (the page raises the vendored template's and svgkit's 10 and 10.5px labels as it writes its CSS; both files stay byte-identical). The header prints the plain name, Decision record; the code name moves to the engineers' fold. Public copy, on the page and in the Markdown twin, prints none of record, bet, the bar, PRD, ARR or tokens beyond the page's own name: "What the record read" is "What this read", "9,000 tokens of AI usage per task" is "AI usage of 9,000 per task", and a missing portfolio says to run the portfolio review. With nothing open, the record key's next step reads "No open decisions on this project." Tests for each.
- Tests: the picture draws only figures the page prints, no status colour anywhere, brass only for a person's call, the aria-label states the answer, public copy uses the plain words, the page follows the anatomy, and the vendored svgkit matches its pin.

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
