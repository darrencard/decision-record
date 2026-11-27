# Decision log format (v1)

One Markdown file. `scripts/record.py` writes every record and `scripts/declog.py` parses every record back, so a log written by the scripts always round-trips. Change it through the scripts, not by hand, so every record stays valid. `record.py validate` checks a whole log.

```markdown
## D-0001: Quote drafts need the tradesperson's approval before they send

- Status: decided
- Decision: Every quote the assistant drafts waits for the tradesperson to approve it before it goes to the customer.
- Options considered:
  - Auto-send every draft
  - Approve before send
  - Auto-send under a value threshold
- Chosen: Approve before send
- Decided by: Head of Product, Quoting squad
- Date: 2026-11-12
- Owner: Lead, Quoting squad
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

(Illustrative. Acme and everyone in it are invented.)

| Field | Values | Required |
|---|---|---|
| Status | open, decided, dropped | always |
| Decision | one sentence | decided |
| Options considered | one sub-bullet per option | no (a warning below two) |
| Chosen | one of the options | no |
| Decided by | one person's name, or one role scoped to one team: "<role>, <team or squad>" | decided |
| Date | YYYY-MM-DD, not after today | decided |
| Owner | who carries it out | no (warning) |
| Review by | YYYY-MM-DD, not before Date | no (warning) |
| Reversible | yes, no, unknown | no (warning) |
| Success signal | the result that would show it worked: metric, threshold, date | no (warning); required for Outcome worked |
| Assumptions | one sub-bullet per assumption | no |
| Opened | YYYY-MM-DD | no (without it a call cannot age) |
| Waiting on | one person's name, or one scoped role | open (warning) |
| Decide by | YYYY-MM-DD, the date the call is needed by; becomes the Leader Report deadline | no (warning once passed) |
| Recommendation | who recommends what, from the source | no |
| Source | where the text came from | no |
| Evidence | the decider's words, verbatim; Date must match the line's date when the source dates it | decided |
| Outcome | worked, pending, missed (a log from before 0.3.0 may say landed, watch, stalled; they read as these) | no; decided only |
| Outcome date | YYYY-MM-DD | with Outcome |
| Outcome evidence | the result and where it came from | with Outcome worked |
| Dropped because | the reason | dropped |
| Notes | free text | no |

Empty fields are left out. Every value is one line: newlines in source text are collapsed, so a value can never start a new field or a new record.
