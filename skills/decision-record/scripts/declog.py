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
# A decision's outcome: did the call do what its success signal said? These are not a bet's status
# words. Landed, watch and stalled belong to a bet and only did-it-land sets them (Landing Loop contract).
OUTCOMES = ("worked", "pending", "missed")
# Logs written before 0.3.0 used the bet words for outcomes. They are read as the new words.
LEGACY_OUTCOMES = {"landed": "worked", "watch": "pending", "stalled": "missed"}

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
    ("Success signal", "success_signal"),
    ("Assumptions", "assumptions"),
    ("Opened", "opened"),
    ("Waiting on", "waiting_on"),
    ("Decide by", "decide_by"),
    ("Recommendation", "recommendation"),
    ("Source", "source"),
    ("Evidence", "evidence"),
    ("Outcome", "outcome"),
    ("Outcome date", "outcome_date"),
    ("Outcome evidence", "outcome_evidence"),
    ("Dropped because", "dropped_because"),
    ("Notes", "notes"),
)
LABEL_TO_ATTR = {label.lower(): attr for label, attr in FIELDS}
DATE_FIELDS = ("date", "review_by", "opened", "outcome_date", "decide_by")
LIST_ATTRS = ("options", "assumptions")
# Below these counts a median or a rate is noise, so the reads say so instead of printing one.
MIN_HISTORY_FOR_MEDIAN = 3
MIN_OUTCOMES_FOR_RATE = 5

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
    "tech", "technical", "engineer", "engineers", "designer", "analyst", "researcher", "architect", "general",
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
    success_signal: str | None = None
    assumptions: list[str] = field(default_factory=list)
    opened: str | None = None
    waiting_on: str | None = None
    decide_by: str | None = None
    recommendation: str | None = None
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


# Words that name a unit of people. A scoped role names one ("Quoting squad"); a person's name never holds one.
TEAM_WORDS = {"squad", "team", "group", "guild", "tribe", "pod", "department", "dept", "chapter", "crew", "unit", "function", "org", "organisation", "organization"}
# Connecting words that may sit inside a role ("Head of Product") but say nothing on their own.
FILLER = {"of", "the", "and", "&", "for"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\-]*", text)


def is_person_name(name: str | None) -> bool:
    """True for a person's name: "Maya Ortiz", "Maya Ortiz (VP Product)", "Raj".

    A name holds no role word and no team word outside brackets, so "Quoting squad lead",
    "Head of Engineering", "the team" and "TBD" are not names, however they are capitalised."""
    n = clean(name)
    if not n or "," in n:
        return False
    core = re.sub(r"\s*\(.*?\)\s*", " ", n).strip()
    if not core or core.lower() in COLLECTIVE:
        return False
    tokens = _tokens(core)
    if not tokens or any(t.lower() in ROLE_WORDS or t.lower() in TEAM_WORDS for t in tokens):
        return False
    return any(t[0].isupper() for t in tokens)


def is_scoped_role(name: str | None) -> bool:
    """True for a role scoped to one team, written "<role>, <team or squad>":
    "Head of Product, Quoting squad", "Lead, Quoting squad", "Tech lead, Payments team".

    The role is role words only (it names a seat, not a group). The scope names one unit: it ends
    in a team word and has at least one word of its own before it ("Quoting"). A bare role
    ("Head of Engineering"), a role with no comma ("Quoting squad lead"), or a scope with no
    name of its own ("Lead, the squad") is not scoped."""
    n = clean(name)
    if not n or n.count(",") != 1:
        return False
    role, scope = (part.strip() for part in n.split(","))
    role_t, scope_t = _tokens(role), _tokens(scope)
    if not role_t or not scope_t or role.lower() in COLLECTIVE:
        return False
    if not all(t.lower() in ROLE_WORDS and t.lower() not in TEAM_WORDS for t in role_t) or all(t.lower() in FILLER for t in role_t):
        return False
    if scope_t[-1].lower() not in TEAM_WORDS:
        return False
    own = [t for t in scope_t[:-1] if t.lower() not in FILLER and t.lower() not in TEAM_WORDS]
    return bool(own) and not any(t.lower() in COLLECTIVE for t in own)


def is_named_decider(name: str | None) -> bool:
    """The decider rule: one person's name, or one role scoped to one team. Nothing else."""
    return is_person_name(name) or is_scoped_role(name)


# Kept for callers of 0.2.0 and earlier: the same rule.
is_named_person = is_named_decider


# ---------------------------------------------------------------- the format


def record_from_dict(d: dict) -> Record:
    r = Record()
    for key in ("id", "title", *[a for _, a in FIELDS]):
        if key not in d:
            continue
        v = d[key]
        if key in LIST_ATTRS:
            items = v if isinstance(v, list) else ([v] if v else [])
            setattr(r, key, [c for c in (clean(x) for x in items) if c])
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
        if attr in LIST_ATTRS:
            items = getattr(r, attr)
            if items:
                lines.append(f"- {label}:")
                lines.extend(f"  - {clean(o)}" for o in items)
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
    in_list: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEADING_RE.match(line)
        if m:
            cur = Record(id=m.group(1), title=m.group(2).strip())
            records.append(cur)
            in_list = None
            continue
        if cur is None:
            continue
        sub = SUBITEM_RE.match(line)
        if sub and in_list:
            item = clean(sub.group(1))
            if item:
                getattr(cur, in_list).append(item)
            continue
        fm = FIELD_RE.match(line)
        if fm:
            attr = LABEL_TO_ATTR.get(fm.group(1).strip().lower())
            in_list = attr if attr in LIST_ATTRS else None
            if attr and attr not in LIST_ATTRS:
                value = clean(fm.group(2))
                if attr == "outcome" and value:
                    value = LEGACY_OUTCOMES.get(value.lower(), value)
                setattr(cur, attr, value)
            continue
        if line.strip():
            in_list = None
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
DATE_HEADER = re.compile(r"^(?:date|meeting date|when)\s*:\s*(20\d{2}-\d{2}-\d{2})\b", re.IGNORECASE)


def parse_source(text: str) -> list[dict]:
    """Split a thread, notes or transcript into utterances: line, speaker, text, date.

    The date is the one in the line's own timestamp, else the last `Date: YYYY-MM-DD`
    header above it, else None. It is never guessed."""
    out = []
    header_date: str | None = None
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        hm = DATE_HEADER.match(line)
        if hm:
            header_date = hm.group(1)
        hit = None
        for pat in SPEAKER_PATTERNS:
            m = pat.match(line)
            if m:
                hit = m
                break
        ts = hit.groupdict().get("ts") if hit else None
        ts_date = DATE_IN_TEXT.search(ts or "")
        when = ts_date.group(1) if ts_date else header_date
        if hit:
            out.append({"line": i, "speaker": clean(hit.group("who")), "text": clean(hit.group("text")) or "", "date": when})
        else:
            out.append({"line": i, "speaker": None, "text": clean(line) or "", "date": when})
    return out


def speakers(utterances: list[dict]) -> list[str]:
    seen: list[str] = []
    for u in utterances:
        s = u["speaker"]
        if s and s not in seen:
            seen.append(s)
    return seen


def base_name(name: str | None) -> str:
    """A name for matching: no role in brackets, and a Slack handle such as
    '@maya.ortiz' or 'maya_ortiz' reads as 'maya ortiz'."""
    n = re.sub(r"\s*\(.*?\)\s*", " ", name or "").strip().lstrip("@")
    return norm_for_match(re.sub(r"[._]+", " ", n))


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
        elif not is_named_decider(r.decided_by):
            err(
                "decider-not-a-person",
                f"Cannot mark this decided: {r.decided_by!r} is a group or a bare role. Name one person, or one role scoped to its team, such as 'Head of Product, Quoting squad'.",
            )
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
        if r.reversible == "no" and not r.success_signal:
            err("one-way-door-no-signal", "A decision that cannot be undone needs a success signal: say what result would show it worked.")
        if not r.success_signal:
            warn("no-success-signal", "No success signal: nothing says what result would show this worked, so the review has nothing to test.")
        if len(r.options) < 2:
            warn("one-option", "Fewer than two options are recorded, so the record cannot show what was turned down.")
    if r.status == "open":
        if r.decided_by:
            err("open-with-decider", "An open record has a decider. Mark it decided, or clear the decider.")
        db = parse_date(r.decide_by)
        if db and db < as_of:
            warn("decide-by-passed", f"The decide-by date {r.decide_by} has passed and the call is still open.")
        if not r.opened:
            warn("no-opened-date", "No opened date, so this cannot age. No age is made up.")
        if not r.waiting_on:
            warn("waiting-on-nobody", "Waiting on nobody: name the person the call needs.")
        elif not is_named_decider(r.waiting_on):
            warn("waiting-on-not-a-person", f"{r.waiting_on!r} is a group or a bare role. Name one person, or one role scoped to its team, such as 'Lead, Quoting squad'.")
    if r.status == "dropped" and not r.dropped_because:
        err("drop-without-reason", "A dropped record needs the reason it was dropped.")

    if r.outcome:
        if r.outcome not in OUTCOMES:
            err("outcome-invalid", f"Outcome must be worked, pending or missed; got {r.outcome!r}.")
        if r.status != "decided":
            err("outcome-on-undecided", "Only a decided record has an outcome.")
        if r.outcome == "worked" and not r.success_signal:
            err("worked-without-signal", "Worked needs a success signal to test the result against. Add what result was expected, or read it as pending.")
        if r.outcome == "worked" and not r.outcome_evidence:
            err("worked-without-evidence", "Worked needs evidence of the result. Without it, the most it can say is pending.")
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
            elif r.status == "decided" and r.date and hit.get("date") and hit["date"] != r.date:
                err("date-not-evidence-date", f"The evidence line is dated {hit['date']} in the source, but the record says {r.date}.")
            if hit and r.status == "decided" and r.decided_by and hit["speaker"] and base_name(hit["speaker"]) != base_name(r.decided_by):
                warn("evidence-from-someone-else", f"The evidence line was said by {hit['speaker']}, not {r.decided_by}. Check they made the call.")
        if r.status == "decided" and r.decided_by and is_named_decider(r.decided_by):
            who = base_name(r.decided_by)
            if who not in names and who not in src_norm:
                err("decider-not-in-source", f"{r.decided_by} does not appear in the source, so the call cannot be attributed to them.")
        if r.waiting_on and is_named_decider(r.waiting_on):
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
    time: no opened date means no age. A call is waiting longer than usual when it has
    waited longer than a decision usually takes here (the median days-to-decide in this
    log, or the expected days the caller sets). It is past due only when its decide-by
    date has passed. It escalates when it has waited `escalate_after` days longer than
    usual and nobody is named to make it.
    """
    history = days_to_decide(records)
    enough = len(history) >= MIN_HISTORY_FOR_MEDIAN
    if expected_days is not None:
        usual, basis = expected_days, "set by the user"
    elif enough:
        usual, basis = median([float(x) for x in history]), f"median of {len(history)} decided records"
    else:
        usual = None
        basis = f"only {len(history)} decided record(s) with an opened date; {MIN_HISTORY_FOR_MEDIAN} are needed for a median, or set --usual-days"
    items = []
    for r in records:
        if r.status != "open":
            continue
        opened = parse_date(r.opened)
        age = days_between(opened, as_of) if opened else None
        on_whom = r.waiting_on if is_named_decider(r.waiting_on) else None
        waiting_long = age is not None and usual is not None and age > usual
        deadline = parse_date(r.decide_by)
        past_due = deadline is not None and deadline < as_of
        escalated = on_whom is None and age is not None and usual is not None and age > usual + escalate_after
        items.append(
            {
                "id": r.id,
                "title": r.title or r.decision,
                "opened": r.opened,
                "days_waiting": age,
                "waiting_on": on_whom,
                "decide_by": r.decide_by,
                "waiting_phrase": wait_phrase(age, waiting_long, usual, r.decide_by if past_due else None),
                "owner_phrase": f"Waiting on {on_whom}" if on_whom else "Waiting on nobody named",
                "waiting_long": waiting_long,
                "past_due": past_due,
                "escalated": escalated,
            }
        )
    items.sort(key=lambda i: (-(i["days_waiting"] if i["days_waiting"] is not None else -1), i["id"]))
    return {
        "as_of": as_of.isoformat(),
        "usual_days_to_decide": usual,
        "usual_basis": basis,
        "escalate_after_days": escalate_after,
        "items": items,
        "counts": {
            "open": len(items),
            "waiting_long": sum(1 for i in items if i["waiting_long"]),
            "past_due": sum(1 for i in items if i["past_due"]),
            "escalated": sum(1 for i in items if i["escalated"]),
            "waiting_on_nobody": sum(1 for i in items if not i["waiting_on"]),
            "ageless": sum(1 for i in items if i["days_waiting"] is None),
        },
        "headline": headline(items),
    }


def wait_phrase(age: int | None, waiting_long: bool, usual: float | None, passed_deadline: str | None = None) -> str:
    """How long a call has waited. "Longer than usual" is against the log's usual time to
    decide; "past due" is only ever a decide-by date that has passed."""
    due = f", past due since {passed_deadline}" if passed_deadline else ""
    if age is None:
        return "No opened date, so no age" + due
    if waiting_long and usual is not None:
        over = age - usual
        return f"{age} day{'' if age == 1 else 's'} waiting, {over:g} longer than the usual {usual:g}" + due
    if age == 0:
        return "Opened today" + due
    return f"{age} day{'' if age == 1 else 's'} waiting" + due


def headline(items: list[dict]) -> str:
    """'4 open · oldest 12 days · 1 waiting longer than usual · 1 past due'. A clause appears only when it is true."""
    if not items:
        return "No open decisions in the log."
    parts = [f"{len(items)} open"]
    ages = [i["days_waiting"] for i in items if i["days_waiting"] is not None]
    if ages:
        oldest = max(ages)
        parts.append("all opened today" if oldest == 0 else f"oldest {oldest} day{'' if oldest == 1 else 's'}")
    long_ = sum(1 for i in items if i["waiting_long"])
    if long_:
        parts.append(f"{long_} waiting longer than usual")
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
    a decision nobody has checked is not counted as worked or as missed."""
    decided = [r for r in records if r.status == "decided"]
    read = [r for r in decided if r.outcome in OUTCOMES]
    worked = [r for r in read if r.outcome == "worked"]
    pending = [r for r in read if r.outcome == "pending"]
    missed = [r for r in read if r.outcome == "missed"]
    review_due = []
    for r in decided:
        rb = parse_date(r.review_by)
        if r.outcome is None and rb and rb <= as_of:
            review_due.append(
                {
                    "id": r.id,
                    "title": r.title or r.decision,
                    "review_by": r.review_by,
                    "days_overdue": (as_of - rb).days,
                    "owner": r.owner,
                    "success_signal": r.success_signal,
                    "assumptions": list(r.assumptions),
                }
            )
    review_due.sort(key=lambda x: (-x["days_overdue"], x["id"]))
    history = days_to_decide(records)
    return {
        "as_of": as_of.isoformat(),
        "decided": len(decided),
        "outcome_read": len(read),
        "not_yet_read": len(decided) - len(read),
        "worked": len(worked),
        "pending": len(pending),
        "missed": len(missed),
        "follow_through_rate_pct": round(len(worked) / len(read) * 100) if len(read) >= MIN_OUTCOMES_FOR_RATE else None,
        "rate_basis": (
            f"{len(worked)} worked of {len(read)} decisions with an outcome read"
            if len(read) >= MIN_OUTCOMES_FOR_RATE
            else f"{len(read)} outcome(s) read; {MIN_OUTCOMES_FOR_RATE} are needed before a rate means anything"
        ),
        "median_days_to_decide": median([float(x) for x in history]) if len(history) >= MIN_HISTORY_FOR_MEDIAN else None,
        "days_to_decide_basis": f"{len(history)} decided records with an opened date",
        "without_success_signal": sum(1 for r in decided if not r.success_signal),
        "one_way_doors": sum(1 for r in decided if r.reversible == "no"),
        # The validator refuses these, so this is 0 unless someone edited the log by hand.
        "no_decider_named": sum(1 for r in decided if not is_named_decider(r.decided_by)),
        "missed_rows": [{"id": r.id, "title": r.title or r.decision, "owner": r.owner, "outcome_date": r.outcome_date} for r in missed],
        "review_due": review_due,
    }


# ------------------------------------------------- the Leader Report decision format

# The Product & Technology Leader Report reads decisions from a table with these columns
# (intake.py IMPORTS["decisions"]) and draws each one on its decision slide as
# "Options: A or B. Deadline: D." (draft.py), which render.py splits back into options on
# ", or" and " or ". Pinned to the Leader Report at commit 366da9b. Extra columns are ignored
# by its reader, so owner, days waiting, id and source travel with each row for the ledger.
LEADER_REPORT_COLUMNS = ("ask", "options", "recommendation", "deadline")
LEADER_REPORT_EXTRA = ("owner", "days_waiting", "id", "source")
OPTION_SPLIT = re.compile(r",? or ")


def leader_report_rows(records: list[Record], as_of: date, expected_days: float | None = None, escalate_after: int = 14) -> tuple[list[dict], list[Finding]]:
    """Open decisions as rows in the Leader Report's decision format, oldest first.

    Refuses (returns findings) when the Leader Report would misread a row: an option that
    holds the word "or", which the slide would split into two options."""
    by_id = {r.id: r for r in records}
    q = open_queue(records, as_of, expected_days, escalate_after)
    rows, problems = [], []
    for item in q["items"]:
        r = by_id[item["id"]]
        options = [o.rstrip(". ") for o in r.options]
        for o in options:
            if OPTION_SPLIT.search(f" {o} "):
                msg = f"The option {o!r} contains the word 'or', so the decision slide would show it as two options. Reword it."
                problems.append(Finding("option-splits-on-the-slide", "error", r.id, msg))
        wait = f"Waiting on {item['waiting_on']}" if item["waiting_on"] else "Nobody is named to make this call"
        if item["days_waiting"] is not None:
            wait += f", {item['days_waiting']} day{'' if item['days_waiting'] == 1 else 's'} open"
        if item["escalated"]:
            wait += ", escalated"
        elif item["waiting_long"]:
            wait += f", longer than the usual {q['usual_days_to_decide']:g} days to decide"
        if item["past_due"]:
            wait += f", past due since {r.decide_by}"
        wait += "."
        rec = f"{r.recommendation.rstrip('.')}. {wait}" if r.recommendation else f"No recommendation recorded. {wait}"
        rows.append(
            {
                "ask": r.title or r.decision,
                "options": " or ".join(options) or None,
                "recommendation": rec,
                "deadline": r.decide_by,
                "owner": item["waiting_on"],
                "days_waiting": item["days_waiting"],
                "id": r.id,
                "source": r.source,
            }
        )
    return rows, problems


def leader_report_markdown(rows: list[dict], as_of: date) -> str:
    cols = LEADER_REPORT_COLUMNS + LEADER_REPORT_EXTRA

    def cell(v: object) -> str:
        return "" if v is None else str(v).replace("|", "\\|")

    out = [
        f"Open decisions as of {as_of.isoformat()}, from the decision log. Import with the Leader Report: intake.py import run/intake.json --decisions this-file.md",
        "",
        "| " + " | ".join(cols) + " |",
        "|" + "---|" * len(cols),
    ]
    out += ["| " + " | ".join(cell(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(out) + "\n"
