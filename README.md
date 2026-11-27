# No decision without a named decider

A free Claude skill that turns a thread, meeting notes or a transcript into a decision record, and refuses to call anything decided until one named person made the call.

## Paste this into Claude Code

```text
Install the decision-record skill: run /plugin marketplace add darrencard/landing-loop, then /plugin install decision-record@landing-loop. Then read the decisions in the thread I point you to (Slack or Linear through the connectors in this session, through the skill's from_thread.py; or the text I paste), write one record per call, check each against the source with the skill's scripts, show me the records and any warnings, and append them to decisions.md after I say yes. If nobody named made a call, log it as open and tell me who it waits on. Then list the open decisions with days waiting and on whom.
```

**What it does:** writes each call to a log with the one person who made it and their words from the source, and lists the calls still waiting, on whom, for how long.

**Why it matters:** most teams lose decisions in threads. Weeks later nobody can say who decided, what was turned down, or what result the call was meant to bring.

**Where it sits:** step 01 (Decide) of the Landing Loop. It reads the bet's landing brief and the `portfolio` key bet-portfolio-review wrote, writes only its `decisions` key in `landing/<bet>.json`, and feeds the Leader Report's decision slide unchanged.

**How it works:** Python checks every record against the source before it is written. The decider's words must be in the source, word for word, on the date the record gives. "The team" or "leadership" is not a decider, so the call is logged as open, waiting on a named person. Code computes every count and age. The model never does the maths.

## Try it in one minute

Acme is invented: invoicing software for trades businesses. Every person, figure and date is illustrative. From a fresh clone, with Python 3.11 or later:

```bash
python3 examples/acme/sample.py
```

It reads Acme's decide call of 2026-07-27 ([sources/](examples/acme/sources)), checks five draft records against it, and writes [examples/acme/decision-record.html](examples/acme/decision-record.html), its Markdown twin, the log [decisions.md](examples/acme/decisions.md), and the `decisions` key of [landing/quote-drafting.json](examples/acme/landing/quote-drafting.json). It starts from the landing-loop record filtered to the keys it reads ([upstream/](examples/acme/upstream)). A test checks the command reproduces every committed file byte for byte.

```text
3 decided, 2 open. 1 past due: D-0004 has waited 14 days on Quoting squad lead, against a usual 7.
Next step: D-0004 waits on Quoting squad lead: set the rollback trigger for quote drafting by 2026-08-03.
```

## Install

In Claude Code:

```text
/plugin marketplace add darrencard/landing-loop
/plugin install decision-record@landing-loop
```

Standalone: clone this repository and copy `skills/decision-record` into `~/.claude/skills/decision-record`. Run the tests with `python3 -m unittest discover -s evals` (or `python3 -m pytest evals`).

## Reads and writes

| | |
|---|---|
| Reads | The source: a Slack thread or Linear comments through `from_thread.py` (live first), or a CSV or pasted text as the fallback. The bet's landing brief, through the Leader Report's own parser. The `portfolio` key, if bet-portfolio-review wrote it. |
| Writes | `decisions.md`, an append-only log your team can diff. The `decisions` key of `landing/<bet>.json`, and nothing else in it. One HTML page in the Leader Report style, and its Markdown twin. |

Your own bet, once the records are in the log:

```bash
python3 skills/decision-record/scripts/open_decisions.py --log decisions.md --as-of 2026-07-27 \
  --loop . --bet quote-drafting --html decisions.html --md decisions-read.md
```

## The record key

Open decisions go in `rows`, in the Leader Report's decision format (`ask`, `options`, `recommendation`, `deadline`, plus `owner`, `days_waiting`, `id`, `source`), so its decision slide reads them unchanged. Every figure carries value, unit, source, window and as_of. Shortened from the Acme record:

```json
"decisions": {
  "tool": "decision-record 0.3.0",
  "as_of": "2026-07-27",
  "columns": ["ask", "options", "recommendation", "deadline", "owner", "days_waiting", "id", "source"],
  "rows": [{"ask": "Set the rollback trigger for quote drafting", "options": "Roll back when wrong-price quotes pass 2% or Roll back when rejected drafts pass 30%",
            "recommendation": "The Quoting squad product manager recommends the wrong-price trigger at 2%. Waiting on Quoting squad lead, 14 days open, past the usual 7 days to decide.",
            "deadline": "2026-08-03", "owner": "Quoting squad lead", "days_waiting": 14, "id": "D-0004", "source": "Acme decide call, 2026-07-27 (illustrative)"}],
  "decided": [{"id": "D-0001", "title": "Build quote drafting now, against its landing brief", "decided_by": "Head of Product, Quoting squad", "date": "2026-07-27"}],
  "brief": {"metric": "Quote draft acceptance rate", "bar": "40%", "by": "2026-11-15", "tested_by": ["D-0001"]},
  "figures": {"past_due": {"value": 1, "unit": "decisions", "source": "decision-record 0.3.0: counted from decisions.md (sha256 1de81b65e887)",
              "window": {"from": "2026-07-13", "to": "2026-07-27"}, "as_of": "2026-07-27"}},
  "next_step": "D-0004 waits on Quoting squad lead: set the rollback trigger for quote drafting by 2026-08-03."
}
```

Its words are a decision's own: open, decided, dropped, past due. A decision's outcome, read later, is worked, pending or missed. A bet's status belongs to did-it-land alone.

## What you get

| Feature | What it does for you |
|---|---|
| Named decider rule | No decision in the log that nobody owns |
| Evidence check | Every record traces back to the moment, and the words, of the call |
| Open decisions | The stuck calls and the people they wait on, oldest first, past due against the log's own median time to decide |
| Success signal | Each call names the result that would show it worked; the bet's own call names the brief's bar |
| Leader Report feed | The board deck shows the same calls, owners and deadlines as the log |
| Append-only log, ADR export, CI check | `record.py validate` blocks a hand-edited record in review; `record.py adr` writes `docs/adr/` |

## Limits

- It records who made a call. It does not judge whether the call was right.
- A source it cannot read is a source it cannot check: save threads and transcripts as text first.
- The Slack and Linear readers are tested on documented response shapes, not yet on a live workspace.
- The usual time to decide needs 3 decided records with an opened date; a follow-through rate needs 5 outcomes read. Below that it prints counts, not a rate.

## Go deeper

- [SKILL.md](skills/decision-record/SKILL.md): the workflow and every rule the validator enforces.
- [references/log-format.md](skills/decision-record/references/log-format.md): the log format.

Version 0.3.0. Not yet run on a real team's data. Python 3.11 or later, standard library only, no network calls. MIT licence. Made by [Dacard](https://www.dacard.ai).

Claude and Claude Code are trademarks of Anthropic, PBC. These skills are independent and not affiliated with or endorsed by Anthropic.
