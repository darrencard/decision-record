# No decision without a named decider

A free Claude skill that turns a Slack thread, meeting notes or a transcript into a decision record, and refuses to call anything decided until one named person made the call.

**Why it matters:** most teams lose decisions in threads. Weeks later nobody can say who decided, what was turned down, or whether it worked. This skill writes each call to a log you can diff, and shows which calls are still waiting, on whom, and for how long.

**How it works:** Python checks every record against the source before it is written. The decider's words must be in the source, word for word, on the date the record gives. "The team" or "leadership" is not a decider, so the record is logged as open, waiting on a named person. Each call states the result that would show it worked, and nothing is marked landed without evidence against it. Code computes every age and count. The model never does the maths.

## Install: paste this into Claude Code

```text
Install the decision-record skill from https://github.com/darrencard/decision-record: copy skills/decision-record into ~/.claude/skills/decision-record and run its tests with python3 -m unittest discover -s evals. Then read the thread I paste next, write a decision record for each call in it, check each one against the thread with the skill's scripts, show me the records and any warnings, and append them to decisions.md after I say yes. If nobody named made a call, log it as open and tell me who it is waiting on.
```

Your first record comes back from the first thread you paste. Then ask "which decisions are open?" for days waiting, on whom, and what is past due.

## A record

```markdown
## D-0001: Quote drafts need the tradesperson's approval before they send

- Status: decided
- Decision: Every quote the assistant drafts waits for the tradesperson to approve it before it goes to the customer.
- Options considered:
  - Auto-send every draft
  - Approve before send
  - Auto-send under a value threshold
- Chosen: Approve before send
- Decided by: Maya Ortiz
- Date: 2026-11-12
- Owner: Tom Okafor
- Review by: 2026-12-15
- Reversible: yes
- Success signal: Wrong-line-item complaints fall below 5 a month by 2026-12-15 (illustrative), with quote send time no more than 1 day slower.
- Assumptions:
  - Most wrong line items are caught when the tradesperson reads the draft
  - Approving each draft adds under a minute per quote
- Opened: 2026-11-10
- Source: Slack #quotes-squad thread, 2026-11-10 to 2026-11-12 (illustrative)
- Evidence: My call: we go with approve before send for every drafted quote.
```

*Acme and everyone in it are invented.*

## What you get

| Feature | What it does | What it does for you |
|---|---|---|
| Named decider rule | Refuses `decided` without one named person and their words from the source | No decision in the log that nobody owns |
| Evidence check | Matches the decider's line to the source word for word, and its date to the line's timestamp | Any record traces back to the moment the call was made |
| Success signal | Each call names the result that would show it worked; landed needs evidence against it | Reviews test a stated result, not a feeling |
| One record per call | Decision, options, chosen option, decider, date, owner, review date, reversible | What was turned down and when to check it worked, in one place |
| Open decisions | Days waiting, on whom, past due against the log's own median time to decide | The stuck calls and the people they wait on, oldest first |
| Follow-through | Landed, watch and stalled on past calls; a rate only once 5 outcomes are read | Whether the calls you made turned into results, without a rate built on three data points |
| Append-only log | One Markdown file; new records go on the end, old ones stay byte for byte; `record.py validate` runs in CI | A record your team can read, diff and review in a pull request |
| ADR export | `record.py adr` writes one ADR file per record into `docs/adr/` | Fits the way engineering teams already keep decisions |
| Local | Python standard library only, no network calls, MIT licensed | Thread content never leaves your machine |

## Example

`evals/fixtures/` holds two sources for Acme, an invented invoicing company for trades businesses: a Slack thread where a named VP makes a clear call, and meeting notes where nobody does. The first becomes a decided record. The second is refused as decided ("the team" is not a person) and logged as open, waiting on the finance lead. All names, figures and dates are illustrative.

```bash
cd skills/decision-record
python3 scripts/open_decisions.py --log ../../evals/fixtures/sample_log.md --as-of 2026-11-26
```

```text
4 open · oldest 29 days · 2 past due · 2 waiting on nobody named
Usual time to decide: 8 days (median of 4 decided records).
Follow-through: no rate yet (3 outcome(s) read; 5 are needed before a rate means anything). landed 1 · watch 1 · stalled 1 · not yet read 1.
```

(Excerpt. The full output also lists each open call with its days waiting and on whom.)

## Scripts

| Script | Job |
|---|---|
| `scan.py` | Lists speakers, dates and the lines that sound like a call made, deferred or asked |
| `record.py` | `check`, `append`, `decide`, `drop`, `outcome`, `validate`, `adr`. Exit 2 when a rule refuses, and nothing is written |
| `open_decisions.py` | Open decisions with days waiting and on whom, and follow-through |
| `declog.py` | The log format, the validation rules and both reads |

To block a hand-edited record in review, add one step to CI:

```bash
python3 skills/decision-record/scripts/record.py validate --log decisions.md --as-of "$(date +%F)"
```

The rules are listed in [SKILL.md](skills/decision-record/SKILL.md) and the log format in [references/log-format.md](skills/decision-record/references/log-format.md). The ageing logic is ported from Throughline's decision queue.

## Status

Version 0.1.0. Tested on the Acme fixtures only, not yet on a real team's threads. Python 3.9 or later. Tests: `python3 -m unittest discover -s evals -v`.

MIT licensed. Made by [Dacard](https://www.dacard.ai).
