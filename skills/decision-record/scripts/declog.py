"""The decision log: its format, its validation rules and its two reads.

The log is one Markdown file that people can read and diff. This module owns the
format: it writes every record and parses every record back, so a log written by
these scripts always round-trips. Nothing here does any arithmetic the caller has
to trust blindly: every age and rate is computed from dates and counts in the log,
and every rule that refuses a record is named and tested.

Pure. No clock and no I/O beyond what the caller passes in: `as_of` is always an
argument, so the same log read on the same date gives the same answer.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

LOG_HEADER = "# Decision log\n\n<!-- decision-record log v1. Written by scripts/record.py. Change it through the scripts so every record stays valid. -->\n"

STATUSES = ("open", "decided", "dropped")
REVERSIBLE = ("yes", "no", "unknown")
# The follow-through read uses the only status vocabulary there is.
OUTCOMES = ("landed", "watch", "stalled")

# Field label in the Markdown, attribute name on the record. Order is the write order.
FIELDS: tuple[tuple[str, str], ...] = (
    ("Status", "status"),
    ("Decision", "decision"),
    ("Options considered", "options"),
    ("Chosen", "chosen"),
    ("Decided by", "decided_by"),
    ("Date", "date"),
    ("Owner", "owner"),
    ("Review by", "review_by"),
    ("Reversible", "reversible"),
    ("Opened", "opened"),
    ("Waiting on", "waiting_on"),
    ("Source", "source"),
    ("Evidence", "evidence"),
    ("Outcome", "outcome"),
    ("Outcome date", "outcome_date"),
    ("Outcome evidence", "outcome_evidence"),
    ("Dropped because", "dropped_because"),
    ("Notes", "notes"),
)
LABEL_TO_ATTR = {label.lower(): attr for label, attr in FIELDS}
DATE_FIELDS = ("date", "review_by", "opened", "outcome_date")

# Words that name a group, a role or nobody. A record whose decider is only these
# words has no named decider, so it cannot be marked decided.
# fmt: off
COLLECTIVE = {
    "we", "us", "our", "they", "them", "team", "the team", "everyone", "everybody", "all", "all of us",
    "group", "the group", "consensus", "leadership", "management", "the business", "the company",
    "squad", "the squad", "committee", "the committee", "board", "the board", "exec", "execs",
    "tbd", "tbc", "unknown", "n/a", "na", "none", "nobody", "someone", "somebody", "anyone", "?",
}
ROLE_WORDS = {
    "head", "of", "the", "vp", "svp", "evp", "cpo", "cto", "ceo", "coo", "cfo", "cro", "cpto", "chief",
    "director", "lead", "leads", "manager", "managers", "owner", "product", "engineering", "design", "finance",
    "sales", "marketing", "ops", "operations", "data", "platform", "squad", "team", "and", "&", "staff",
    "principal", "senior", "pm", "em", "eng", "officer", "founder", "founders", "partner", "president",
}
# fmt: on

ID_RE = re.compile(r"^D-(\d{4,})$")
HEADING_RE = re.compile(r"^##\s+(D-\d{4,}):\s*(.*)$")
FIELD_RE = re.compile(r"^-\s+([A-Za-z ]+):\s?(.*)$")
SUBITEM_RE = re.compile(r"^\s{2,}-\s+(.*)$")


@dataclass
class Record:
    id: str = ""
    title: str = ""
    status: str = ""
    decision: str | None = None
    options: list[str] = field(default_factory=list)
    chosen: str | None = None
    decided_by: str | None = None
    date: str | None = None
    owner: str | None = None
    review_by: str | None = None
    reversible: str | None = None
    opened: str | None = None
    waiting_on: str | None = None
    source: str | None = None
    evidence: str | None = None
    outcome: str | None = None
    outcome_date: str | None = None
    outcome_evidence: str | None = None
    dropped_because: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("id", "title", *[a for _, a in FIELDS])}


@dataclass
class Finding:
    rule: str
    level: str  # "error" blocks the write; "warning" is reported and allowed
    record: str
    message: str

    def to_dict(self) -> dict:
        return {"rule": self.rule, "level": self.level, "record": self.record, "message": self.message}


# ---------------------------------------------------------------------- text


def clean(value: object) -> str | None:
    """One line of plain text. Text from a thread is data: collapsing newlines means a
    value can never start a new field or a new record in the log."""
    if value is None:
        return None
    s = unicodedata.normalize("NFKC", str(value))
    s = "".join(ch if ch.isprintable() else " " for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def norm_for_match(s: str) -> str:
    """Normalise text for a verbatim-quote check: case, curly quotes and spacing only."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def is_named_person(name: str | None) -> bool:
    """True only for a value that names a person. 'The team', 'we', 'leadership' and a
    bare role such as 'Head of Product' are not names."""
    n = clean(name)
    if not n:
        return False
    # Drop a trailing role in brackets: "Maya Ortiz (VP Product)" -> "Maya Ortiz".
    core = re.sub(r"\s*\(.*?\)\s*", " ", n).strip()
    if not core or core.lower() in COLLECTIVE:
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", core)
    if not tokens:
        return False
    if all(t.lower() in ROLE_WORDS for t in tokens):
        return False
    # A name starts with a capital letter somewhere; "someone in finance" does not.
    return any(t[0].isupper() and t.lower() not in ROLE_WORDS for t in tokens)


# ---------------------------------------------------------------- the format


def record_from_dict(d: dict) -> Record:
    r = Record()
    for key in ("id", "title", *[a for _, a in FIELDS]):
        if key not in d:
            continue
        v = d[key]
        if key == "options":
            items = v if isinstance(v, list) else ([v] if v else [])
            r.options = [c for c in (clean(x) for x in items) if c]
        else:
            setattr(r, key, clean(v))
    for key in ("status", "reversible", "outcome"):
        v = getattr(r, key)
        if v:
            setattr(r, key, v.lower())
    return r


def format_record(r: Record) -> str:
    lines = [f"## {r.id}: {clean(r.title) or ''}".rstrip(), ""]
    for label, attr in FIELDS:
        if attr == "options":
            if r.options:
                lines.append(f"- {label}:")
                lines.extend(f"  - {clean(o)}" for o in r.options)
            continue
        v = clean(getattr(r, attr))
        if v:
            lines.append(f"- {label}: {v}")
    return "\n".join(lines) + "\n"


def format_log(records: list[Record]) -> str:
    return LOG_HEADER + "".join("\n" + format_record(r) for r in records)


def parse_log(text: str) -> list[Record]:
    records: list[Record] = []
    cur: Record | None = None
    in_options = False
    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEADING_RE.match(line)
        if m:
            cur = Record(id=m.group(1), title=m.group(2).strip())
            records.append(cur)
            in_options = False
            continue
        if cur is None:
            continue
        sub = SUBITEM_RE.match(line)
        if sub and in_options:
            item = clean(sub.group(1))
            if item:
                cur.options.append(item)
            continue
        fm = FIELD_RE.match(line)
        if fm:
            attr = LABEL_TO_ATTR.get(fm.group(1).strip().lower())
            in_options = attr == "options"
            if attr and attr != "options":
                setattr(cur, attr, clean(fm.group(2)))
            continue
        if line.strip():
            in_options = False
    return records


def next_id(records: list[Record]) -> str:
    nums = [int(m.group(1)) for m in (ID_RE.match(r.id) for r in records) if m]
    return f"D-{(max(nums) + 1 if nums else 1):04d}"


# ---------------------------------------------------------------- the source


SPEAKER_PATTERNS = (
    # [2026-11-12 09:14] Maya Ortiz: text      (Slack copy)
    re.compile(r"^\[(?P<ts>[^\]]+)\]\s*(?P<who>[^:]{1,60}?):\s+(?P<text>.+)$"),
    # Maya Ortiz (00:12:03): text              (transcript)
    re.compile(r"^(?P<who>[A-Z][^:()]{0,59}?)\s*\((?P<ts>[0-9:]{4,8})\):\s+(?P<text>.+)$"),
    # Maya Ortiz  9:14 AM  text                (Slack desktop copy)
    re.compile(r"^(?P<who>[A-Z][A-Za-z'\-]+(?: [A-Z][A-Za-z'\-]+){0,3})\s{2,}(?P<ts>\d{1,2}:\d{2}(?:\s?[AP]M)?)\s{2,}(?P<text>.+)$"),
    # Maya Ortiz: text                         (notes)
    re.compile(r"^(?P<who>[A-Z][A-Za-z'\-]+(?: [A-Z][A-Za-z'\-]+){0,3}):\s+(?P<text>.+)$"),
)
DATE_IN_TEXT = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def parse_source(text: str) -> list[dict]:
    """Split a thread, notes or transcript into utterances: line, speaker, text."""
    out = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        hit = None
        for pat in SPEAKER_PATTERNS:
            m = pat.match(line)
            if m:
                hit = m
                break
        if hit:
            out.append({"line": i, "speaker": clean(hit.group("who")), "text": clean(hit.group("text")) or ""})
        else:
            out.append({"line": i, "speaker": None, "text": clean(line) or ""})
    return out


def speakers(utterances: list[dict]) -> list[str]:
    seen: list[str] = []
    for u in utterances:
        s = u["speaker"]
        if s and s not in seen:
            seen.append(s)
    return seen


def base_name(name: str | None) -> str:
    return norm_for_match(re.sub(r"\s*\(.*?\)\s*", " ", name or ""))


def find_quote(quote: str, utterances: list[dict]) -> dict | None:
    """The utterance that holds the quote verbatim (case and spacing aside), if any."""
    q = norm_for_match(quote).strip('"').strip("'").strip()
    if not q:
        return None
    for u in utterances:
        if q in norm_for_match(u["text"]):
            return u
    # A quote may include its own speaker prefix ("Maya Ortiz: ..."): try the whole line.
    for u in utterances:
        whole = norm_for_match(f"{u['speaker']}: {u['text']}") if u["speaker"] else norm_for_match(u["text"])
        if q in whole:
            return u
    return None


# ------------------------------------------------------------------- the rules


def validate(r: Record, as_of: date, source_text: str | None = None, existing: list[Record] | None = None) -> list[Finding]:
    """Every rule a record must pass before it is written. Errors block the write."""
    f: list[Finding] = []
    rid = r.id or "(new)"

    def err(rule: str, msg: str) -> None:
        f.append(Finding(rule, "error", rid, msg))

    def warn(rule: str, msg: str) -> None:
        f.append(Finding(rule, "warning", rid, msg))

    if r.status not in STATUSES:
        err("status-invalid", f"Status must be one of {', '.join(STATUSES)}; got {r.status!r}.")
    if not (r.title or r.decision):
        err("no-decision-text", "A record needs a title or a decision statement.")
    if existing and r.id and any(e.id == r.id for e in existing):
        err("duplicate-id", f"{r.id} is already in the log.")

    for attr in DATE_FIELDS:
        v = getattr(r, attr)
        if v and parse_date(v) is None:
            err("date-invalid", f"{attr} must be YYYY-MM-DD; got {v!r}.")
    for attr in ("date", "opened", "outcome_date"):
        d = parse_date(getattr(r, attr))
        if d and d > as_of:
            err("date-in-future", f"{attr} {d.isoformat()} is after the as-of date {as_of.isoformat()}.")

    if r.reversible and r.reversible not in REVERSIBLE:
        err("reversible-invalid", f"Reversible must be yes, no or unknown; got {r.reversible!r}.")
    if r.chosen and r.options and norm_for_match(r.chosen) not in {norm_for_match(o) for o in r.options}:
        err("chosen-not-an-option", "The chosen option is not one of the options considered.")

    if r.status == "decided":
        if not clean(r.decided_by):
            err("no-decider", "Cannot mark this decided: nobody is named as the decider. Log it as open, waiting on a named person.")
        elif not is_named_person(r.decided_by):
            err("decider-not-a-person", f"Cannot mark this decided: {r.decided_by!r} is a group or a role, not a named person.")
        if not r.date:
            err("no-decision-date", "A decided record needs the date the call was made.")
        if not clean(r.evidence):
            err("no-evidence", "A decided record needs the line from the source where the call was made.")
        if not r.decision:
            err("no-decision-text", "A decided record needs the decision, stated in one sentence.")
        dd, rb = parse_date(r.date), parse_date(r.review_by)
        if dd and rb and rb < dd:
            err("review-before-decision", "The review date is before the decision date.")
        if not r.owner:
            warn("no-owner", "No owner carries this out.")
        if not r.review_by:
            warn("no-review-date", "No review date, so follow-through will never be read.")
        if not r.reversible or r.reversible == "unknown":
            warn("reversibility-unknown", "Nobody said whether this can be undone.")
        if r.reversible == "no" and not r.review_by:
            warn("one-way-door-no-review", "A decision that cannot be undone has no review date.")
        if len(r.options) < 2:
            warn("one-option", "Fewer than two options are recorded, so the record cannot show what was turned down.")
    if r.status == "open":
        if r.decided_by:
            err("open-with-decider", "An open record has a decider. Mark it decided, or clear the decider.")
        if not r.opened:
            warn("no-opened-date", "No opened date, so this cannot age. No age is made up.")
        if not r.waiting_on:
            warn("waiting-on-nobody", "Waiting on nobody: name the person the call needs.")
        elif not is_named_person(r.waiting_on):
            warn("waiting-on-not-a-person", f"{r.waiting_on!r} is a group or a role. Name one person.")
    if r.status == "dropped" and not r.dropped_because:
        err("drop-without-reason", "A dropped record needs the reason it was dropped.")

    if r.outcome:
        if r.outcome not in OUTCOMES:
            err("outcome-invalid", f"Outcome must be landed, watch or stalled; got {r.outcome!r}.")
        if r.status != "decided":
            err("outcome-on-undecided", "Only a decided record has an outcome.")
        if r.outcome == "landed" and not r.outcome_evidence:
            err("landed-without-evidence", "Landed needs evidence of the result. Without it, the most it can say is watch.")
        if not r.outcome_date:
            err("outcome-without-date", "An outcome needs the date it was read.")
        od, dd = parse_date(r.outcome_date), parse_date(r.date)
        if od and dd and od < dd:
            err("outcome-before-decision", "The outcome date is before the decision date.")

    if source_text is not None:
        utt = parse_source(source_text)
        names = [base_name(s) for s in speakers(utt)]
        src_norm = norm_for_match(source_text)
        if r.evidence:
            hit = find_quote(r.evidence, utt)
            if hit is None:
                err("evidence-not-in-source", "The evidence quote is not in the source, word for word.")
            elif r.status == "decided" and r.decided_by and hit["speaker"] and base_name(hit["speaker"]) != base_name(r.decided_by):
                warn("evidence-from-someone-else", f"The evidence line was said by {hit['speaker']}, not {r.decided_by}. Check they made the call.")
        if r.status == "decided" and r.decided_by and is_named_person(r.decided_by):
            who = base_name(r.decided_by)
            if who not in names and who not in src_norm:
                err("decider-not-in-source", f"{r.decided_by} does not appear in the source, so the call cannot be attributed to them.")
        if r.waiting_on and is_named_person(r.waiting_on):
            who = base_name(r.waiting_on)
            if who not in names and who not in src_norm:
                warn("waiting-on-not-in-source", f"{r.waiting_on} does not appear in the source.")
    return f


def validate_log(records: list[Record], as_of: date) -> list[Finding]:
    out: list[Finding] = []
    seen: set[str] = set()
    for r in records:
        if not ID_RE.match(r.id):
            out.append(Finding("id-invalid", "error", r.id or "(blank)", "Record ids look like D-0001."))
        if r.id in seen:
            out.append(Finding("duplicate-id", "error", r.id, f"{r.id} appears twice."))
        seen.add(r.id)
        out.extend(validate(r, as_of))
    return out


# ------------------------------------------------------------------- the reads


def days_between(a: date, b: date) -> int:
    """Whole days from a to b, never negative. Day one is the day it opened."""
    return max(0, (b - a).days)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2


def days_to_decide(records: list[Record]) -> list[int]:
    """Days from opened to decided, for every decided record that has both dates."""
    out = []
    for r in records:
        o, d = parse_date(r.opened), parse_date(r.date)
        if r.status == "decided" and o and d and d >= o:
            out.append((d - o).days)
    return out


def open_queue(records: list[Record], as_of: date, expected_days: float | None = None, escalate_after: int = 14) -> dict:
    """The calls still waiting on someone, oldest first.

    Ported from Throughline's decision queue. An age is only ever a measured elapsed
    time: no opened date means no age. A call is past due when it has waited longer
    than a decision usually takes here (the median days-to-decide in this log, or the
    expected days the caller sets). It escalates when it is past due by
    `escalate_after` further days and nobody is named to make it.
    """
    history = days_to_decide(records)
    usual = expected_days if expected_days is not None else median([float(x) for x in history])
    basis = "set by the user" if expected_days is not None else (f"median of {len(history)} decided records" if history else None)
    items = []
    for r in records:
        if r.status != "open":
            continue
        opened = parse_date(r.opened)
        age = days_between(opened, as_of) if opened else None
        on_whom = r.waiting_on if is_named_person(r.waiting_on) else None
        past_due = age is not None and usual is not None and age > usual
        escalated = on_whom is None and age is not None and usual is not None and age > usual + escalate_after
        items.append(
            {
                "id": r.id,
                "title": r.title or r.decision,
                "opened": r.opened,
                "days_waiting": age,
                "waiting_on": on_whom,
                "waiting_phrase": wait_phrase(age, past_due, usual),
                "owner_phrase": f"Waiting on {on_whom}" if on_whom else "Waiting on nobody named",
                "past_due": past_due,
                "escalated": escalated,
            }
        )
    items.sort(key=lambda i: (-(i["days_waiting"] if i["days_waiting"] is not None else -1), i["id"]))
    return {
        "as_of": as_of.isoformat(),
        "usual_days_to_decide": usual,
        "usual_basis": basis,
        "items": items,
        "counts": {
            "open": len(items),
            "past_due": sum(1 for i in items if i["past_due"]),
            "escalated": sum(1 for i in items if i["escalated"]),
            "waiting_on_nobody": sum(1 for i in items if not i["waiting_on"]),
            "ageless": sum(1 for i in items if i["days_waiting"] is None),
        },
        "headline": headline(items),
    }


def wait_phrase(age: int | None, past_due: bool, usual: float | None) -> str:
    if age is None:
        return "No opened date, so no age"
    if past_due and usual is not None:
        over = age - usual
        over_s = f"{over:g}"
        return f"{age} day{'' if age == 1 else 's'} waiting, {over_s} past the usual {usual:g}"
    if age == 0:
        return "Opened today"
    return f"{age} day{'' if age == 1 else 's'} waiting"


def headline(items: list[dict]) -> str:
    """'4 open · oldest 12 days · 1 past due'. A clause appears only when it is true."""
    if not items:
        return "No open decisions in the log."
    parts = [f"{len(items)} open"]
    ages = [i["days_waiting"] for i in items if i["days_waiting"] is not None]
    if ages:
        oldest = max(ages)
        parts.append("all opened today" if oldest == 0 else f"oldest {oldest} day{'' if oldest == 1 else 's'}")
    due = sum(1 for i in items if i["past_due"])
    if due:
        parts.append(f"{due} past due")
    nobody = sum(1 for i in items if not i["waiting_on"])
    if nobody:
        parts.append(f"{nobody} waiting on nobody named")
    return " · ".join(parts)


def follow_through(records: list[Record], as_of: date) -> dict:
    """Of the calls made, how many turned into a result. Ported from Throughline's
    decision log read. The rate counts only decisions whose outcome has been read:
    a decision nobody has checked is not counted as landed or as stalled."""
    decided = [r for r in records if r.status == "decided"]
    read = [r for r in decided if r.outcome in OUTCOMES]
    landed = [r for r in read if r.outcome == "landed"]
    watch = [r for r in read if r.outcome == "watch"]
    stalled = [r for r in read if r.outcome == "stalled"]
    review_due = []
    for r in decided:
        rb = parse_date(r.review_by)
        if r.outcome is None and rb and rb <= as_of:
            review_due.append({"id": r.id, "title": r.title or r.decision, "review_by": r.review_by, "days_overdue": (as_of - rb).days, "owner": r.owner})
    review_due.sort(key=lambda x: (-x["days_overdue"], x["id"]))
    history = days_to_decide(records)
    return {
        "as_of": as_of.isoformat(),
        "decided": len(decided),
        "outcome_read": len(read),
        "not_yet_read": len(decided) - len(read),
        "landed": len(landed),
        "watch": len(watch),
        "stalled": len(stalled),
        "follow_through_rate_pct": round(len(landed) / len(read) * 100) if read else None,
        "rate_basis": f"{len(landed)} landed of {len(read)} decisions with an outcome read" if read else "No outcome has been read yet",
        "median_days_to_decide": median([float(x) for x in history]),
        "days_to_decide_basis": f"{len(history)} decided records with an opened date" if history else None,
        "one_way_doors": sum(1 for r in decided if r.reversible == "no"),
        # The validator refuses these, so this is 0 unless someone edited the log by hand.
        "no_decider_named": sum(1 for r in decided if not is_named_person(r.decided_by)),
        "stalled_rows": [{"id": r.id, "title": r.title or r.decision, "owner": r.owner, "outcome_date": r.outcome_date} for r in stalled],
        "review_due": review_due,
    }
