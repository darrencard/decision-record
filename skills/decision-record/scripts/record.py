"""Check, append and update records in a decision log.

    python3 scripts/record.py check    --draft draft.json --source thread.txt --as-of YYYY-MM-DD
    python3 scripts/record.py append   --draft draft.json --source thread.txt --as-of YYYY-MM-DD --log decisions.md
    python3 scripts/record.py decide   D-0003 --decided-by "Name" --date YYYY-MM-DD --evidence "quote" --source notes.txt --as-of ... --log ...
    python3 scripts/record.py drop     D-0003 --because "reason" --as-of ... --log ...
    python3 scripts/record.py outcome  D-0001 --outcome worked|pending|missed --date YYYY-MM-DD --evidence "..." --as-of ... --log ...
    python3 scripts/record.py validate --log decisions.md --as-of YYYY-MM-DD
    python3 scripts/record.py adr      --log decisions.md --as-of YYYY-MM-DD --out docs/adr

Every command prints JSON. Exit 0: written or valid. Exit 2: refused, with the
rules that refused it. Nothing is written when any error is found.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import declog  # noqa: E402

REFUSED = 2


def load_log(path: Path) -> list[declog.Record]:
    return declog.parse_log(path.read_text(encoding="utf-8")) if path.exists() else []


def emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def errors(findings: list[declog.Finding]) -> list[declog.Finding]:
    return [f for f in findings if f.level == "error"]


def report(action: str, findings: list[declog.Finding], record: declog.Record | None = None, written: bool = False) -> int:
    errs = errors(findings)
    emit(
        {
            "action": action,
            "result": "written" if written else ("refused" if errs else "valid"),
            "record": record.to_dict() if record else None,
            "errors": [f.to_dict() for f in errs],
            "warnings": [f.to_dict() for f in findings if f.level == "warning"],
        }
    )
    return REFUSED if errs else 0


def read_source(path: Path | None) -> str | None:
    return path.read_text(encoding="utf-8") if path else None


def as_of(s: str):
    d = declog.parse_date(s)
    if d is None:
        raise SystemExit(f"--as-of must be YYYY-MM-DD; got {s!r}")
    return d


def write_log(path: Path, records: list[declog.Record]) -> None:
    path.write_text(declog.format_log(records), encoding="utf-8")


def cmd_check(a) -> int:
    rec = declog.record_from_dict(json.loads(a.draft.read_text(encoding="utf-8")))
    existing = load_log(a.log) if a.log else []
    return report("check", declog.validate(rec, as_of(a.as_of), read_source(a.source), existing), rec)


def cmd_append(a) -> int:
    d = as_of(a.as_of)
    existing = load_log(a.log)
    log_errs = errors(declog.validate_log(existing, d))
    if log_errs:
        return report("append", log_errs)
    rec = declog.record_from_dict(json.loads(a.draft.read_text(encoding="utf-8")))
    rec.id = declog.next_id(existing)
    findings = declog.validate(rec, d, read_source(a.source), existing)
    if errors(findings):
        return report("append", findings, rec)
    if not a.log.exists() or not a.log.read_text(encoding="utf-8").strip():
        a.log.write_text(declog.LOG_HEADER, encoding="utf-8")
    # Append, never rewrite: the records already in the log are left byte for byte.
    with a.log.open("a", encoding="utf-8") as fh:
        fh.write("\n" + declog.format_record(rec))
    return report("append", findings, rec, written=True)


def update(a, action: str, change) -> int:
    d = as_of(a.as_of)
    records = load_log(a.log)
    target = next((r for r in records if r.id == a.id), None)
    if target is None:
        emit({"action": action, "result": "refused", "errors": [{"rule": "no-such-record", "record": a.id, "message": f"{a.id} is not in the log."}]})
        return REFUSED
    refusal = change(target)
    if refusal:
        return report(action, [declog.Finding(refusal[0], "error", target.id, refusal[1])], target)
    findings = declog.validate(target, d, read_source(getattr(a, "source", None)))
    if errors(findings):
        return report(action, findings, target)
    write_log(a.log, records)
    return report(action, findings, target, written=True)


def cmd_decide(a) -> int:
    def change(r: declog.Record):
        if r.status != "open":
            return ("not-open", f"{r.id} is {r.status}, not open.")
        r.status = "decided"
        r.decided_by = declog.clean(a.decided_by)
        r.date = declog.clean(a.date)
        r.evidence = declog.clean(a.evidence)
        if a.decision:
            r.decision = declog.clean(a.decision)
        if a.chosen:
            r.chosen = declog.clean(a.chosen)
        for attr in ("owner", "review_by", "reversible", "success_signal"):
            v = getattr(a, attr)
            if v:
                setattr(r, attr, declog.clean(v).lower() if attr == "reversible" else declog.clean(v))
        r.decision = r.decision or r.title
        r.waiting_on = None
        r.decide_by = None
        return None

    return update(a, "decide", change)


def cmd_drop(a) -> int:
    def change(r: declog.Record):
        if r.status != "open":
            return ("not-open", f"{r.id} is {r.status}, not open.")
        r.status = "dropped"
        r.dropped_because = declog.clean(a.because)
        r.waiting_on = None
        return None

    return update(a, "drop", change)


def cmd_outcome(a) -> int:
    def change(r: declog.Record):
        r.outcome = declog.clean(a.outcome).lower()
        r.outcome_date = declog.clean(a.date)
        r.outcome_evidence = declog.clean(a.evidence)
        return None

    return update(a, "outcome", change)


def cmd_validate(a) -> int:
    return report("validate", declog.validate_log(load_log(a.log), as_of(a.as_of)))


def adr_text(r: declog.Record) -> str:
    """One record as an architecture decision record, for teams that keep docs/adr/."""
    status = {"decided": "Accepted", "open": "Proposed", "dropped": "Rejected"}.get(r.status, r.status)
    out = [f"# {r.id}. {r.title or r.decision}", "", f"Status: {status}", ""]
    if r.decided_by or r.date:
        out += [f"Decided by {r.decided_by or 'nobody named'} on {r.date or 'no date'}.", ""]
    out += ["## Context", "", r.source or "Source not recorded.", ""]
    if r.options:
        out += ["## Options considered", "", *[f"- {o}" for o in r.options], ""]
    out += ["## Decision", "", r.decision or r.title, ""]
    if r.evidence:
        out += [f"> {r.evidence}", ""]
    cons = [
        f"- Owner: {r.owner}" if r.owner else None,
        f"- Reversible: {r.reversible}" if r.reversible else None,
        f"- Success signal: {r.success_signal}" if r.success_signal else None,
        f"- Review by: {r.review_by}" if r.review_by else None,
        *[f"- Assumption: {x}" for x in r.assumptions],
        f"- Outcome: {r.outcome} on {r.outcome_date}. {r.outcome_evidence or ''}".rstrip() if r.outcome else None,
        f"- Dropped because: {r.dropped_because}" if r.dropped_because else None,
    ]
    out += ["## Consequences", "", *[c for c in cons if c], ""]
    return "\n".join(out)


def cmd_adr(a) -> int:
    records = load_log(a.log)
    errs = errors(declog.validate_log(records, as_of(a.as_of)))
    if errs:
        return report("adr", errs)
    a.out.mkdir(parents=True, exist_ok=True)
    written = []
    for r in records:
        if a.id and r.id != a.id:
            continue
        slug = "-".join(declog.norm_for_match(r.title or r.id).replace("'", "").split())[:60].strip("-")
        slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
        path = a.out / f"{r.id.lower()}-{slug}.md"
        path.write_text(adr_text(r), encoding="utf-8")
        written.append(str(path))
    emit({"action": "adr", "result": "written", "files": written, "errors": [], "warnings": []})
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, log_required=True):
        sp.add_argument("--as-of", required=True, help="Today's date, YYYY-MM-DD. The scripts keep no clock.")
        sp.add_argument("--log", type=Path, required=log_required)

    s = sub.add_parser("check")
    common(s, log_required=False)
    s.add_argument("--draft", type=Path, required=True)
    s.add_argument("--source", type=Path)
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("append")
    common(s)
    s.add_argument("--draft", type=Path, required=True)
    s.add_argument("--source", type=Path)
    s.set_defaults(fn=cmd_append)

    s = sub.add_parser("decide")
    common(s)
    s.add_argument("id")
    s.add_argument("--decided-by", required=True)
    s.add_argument("--date", required=True)
    s.add_argument("--evidence", required=True)
    s.add_argument("--source", type=Path)
    s.add_argument("--decision")
    s.add_argument("--chosen")
    s.add_argument("--owner")
    s.add_argument("--review-by")
    s.add_argument("--reversible", choices=declog.REVERSIBLE)
    s.add_argument("--success-signal", help="The result that would show this worked, with its metric and threshold.")
    s.set_defaults(fn=cmd_decide)

    s = sub.add_parser("drop")
    common(s)
    s.add_argument("id")
    s.add_argument("--because", required=True)
    s.set_defaults(fn=cmd_drop)

    s = sub.add_parser("outcome")
    common(s)
    s.add_argument("id")
    s.add_argument("--outcome", required=True, choices=declog.OUTCOMES)
    s.add_argument("--date", required=True)
    s.add_argument("--evidence")
    s.set_defaults(fn=cmd_outcome)

    s = sub.add_parser("validate")
    common(s)
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("adr", help="Write records as ADR files, one per record.")
    common(s)
    s.add_argument("--out", type=Path, required=True, help="Folder for the ADR files, for example docs/adr.")
    s.add_argument("--id", help="Only this record.")
    s.set_defaults(fn=cmd_adr)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
