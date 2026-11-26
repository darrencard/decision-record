"""Check, append and update records in a decision log.

    python3 scripts/record.py check    --draft draft.json --source thread.txt --as-of YYYY-MM-DD
    python3 scripts/record.py append   --draft draft.json --source thread.txt --as-of YYYY-MM-DD --log decisions.md
    python3 scripts/record.py decide   D-0003 --decided-by "Name" --date YYYY-MM-DD --evidence "quote" --source notes.txt --as-of ... --log ...
    python3 scripts/record.py drop     D-0003 --because "reason" --as-of ... --log ...
    python3 scripts/record.py outcome  D-0001 --outcome landed|watch|stalled --date YYYY-MM-DD --evidence "..." --as-of ... --log ...
    python3 scripts/record.py validate --log decisions.md --as-of YYYY-MM-DD

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
        for attr in ("owner", "review_by", "reversible"):
            v = getattr(a, attr)
            if v:
                setattr(r, attr, declog.clean(v).lower() if attr == "reversible" else declog.clean(v))
        r.decision = r.decision or r.title
        r.waiting_on = None
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

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
