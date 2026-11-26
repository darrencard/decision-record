"""List open decisions with days waiting and on whom, and read follow-through.

    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --json
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --usual-days 10
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --leader-report run/decisions.md

Every number comes from dates and counts in the log. An open decision with no
opened date has no age: none is made up. The usual time to decide is the median
of this log's own decided records, unless --usual-days sets it.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import declog  # noqa: E402


def build(records: list[declog.Record], as_of, usual_days: float | None, escalate_after: int) -> dict:
    return {
        "open": declog.open_queue(records, as_of, usual_days, escalate_after),
        "follow_through": declog.follow_through(records, as_of),
        "log_errors": [f.to_dict() for f in declog.validate_log(records, as_of) if f.level == "error"],
    }


def markdown(out: dict) -> str:
    q, ft = out["open"], out["follow_through"]
    lines = [f"## Open decisions as of {q['as_of']}", "", q["headline"], ""]
    if q["usual_days_to_decide"] is not None:
        lines += [f"Usual time to decide: {q['usual_days_to_decide']:g} days ({q['usual_basis']}).", ""]
    else:
        lines += [f"Usual time to decide: not known ({q['usual_basis']}), so nothing is marked past due.", ""]
    if q["counts"]["escalated"]:
        lines += [f"Escalate: past due by more than {q['escalate_after_days']} days with nobody named to make the call.", ""]
    if q["items"]:
        lines += ["| Id | Decision needed | Days waiting | Waiting on | Flag |", "|---|---|---|---|---|"]
        for i in q["items"]:
            flag = "escalate" if i["escalated"] else ("past due" if i["past_due"] else "")
            days = "no date" if i["days_waiting"] is None else str(i["days_waiting"])
            lines.append(f"| {i['id']} | {i['title']} | {days} | {i['waiting_on'] or 'nobody named'} | {flag} |")
        lines.append("")
    lines += [f"## Follow-through as of {ft['as_of']}", ""]
    rate = "no rate yet" if ft["follow_through_rate_pct"] is None else f"{ft['follow_through_rate_pct']}%"
    counts = f"landed {ft['landed']} · watch {ft['watch']} · stalled {ft['stalled']} · not yet read {ft['not_yet_read']}"
    lines.append(f"Follow-through: {rate} ({ft['rate_basis']}). {counts}.")
    if ft["stalled_rows"]:
        lines += ["", "Stalled: " + "; ".join(f"{r['id']} {r['title']} (owner: {r['owner'] or 'none'})" for r in ft["stalled_rows"])]
    for r in ft["review_due"]:
        lines += ["", f"Review due: {r['id']} {r['title']}, {r['days_overdue']} days past {r['review_by']} (owner: {r['owner'] or 'none'})."]
        lines.append(f"- Test against: {r['success_signal'] or 'no success signal was recorded'}")
        lines.extend(f"- Assumption to check: {x}" for x in r["assumptions"])
    if ft["without_success_signal"]:
        lines += ["", f"{ft['without_success_signal']} decided record(s) have no success signal, so their review has nothing to test."]
    if out["log_errors"]:
        lines += ["", f"The log has {len(out['log_errors'])} invalid record(s). Run record.py validate."]
    return "\n".join(lines) + "\n"


def write_leader_report(path: Path, rows: list[dict], as_of) -> None:
    if path.suffix.lower() == ".csv":
        cols = declog.LEADER_REPORT_COLUMNS + declog.LEADER_REPORT_EXTRA
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows({c: ("" if r[c] is None else r[c]) for c in cols} for r in rows)
        path.write_text(buf.getvalue(), encoding="utf-8")
    else:
        path.write_text(declog.leader_report_markdown(rows, as_of), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--usual-days", type=float, help="Days a decision should take. Default: the log's own median.")
    p.add_argument("--escalate-after", type=int, default=14, help="Days past due, with nobody named, before a call escalates.")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--leader-report",
        type=Path,
        metavar="FILE",
        help="Also write the open decisions in the Leader Report's decision format (.md or .csv), for intake.py import --decisions.",
    )
    a = p.parse_args(argv)
    d = declog.parse_date(a.as_of)
    if d is None:
        raise SystemExit(f"--as-of must be YYYY-MM-DD; got {a.as_of!r}")
    records = declog.parse_log(a.log.read_text(encoding="utf-8")) if a.log.exists() else []
    out = build(records, d, a.usual_days, a.escalate_after)
    if a.leader_report:
        rows, problems = declog.leader_report_rows(records, d, a.usual_days, a.escalate_after)
        if problems or out["log_errors"]:
            for f in problems:
                print(f"refused: {f.record} {f.rule}: {f.message}", file=sys.stderr)
            if out["log_errors"]:
                print(f"refused: the log has {len(out['log_errors'])} invalid record(s). Run record.py validate.", file=sys.stderr)
            return 2
        write_leader_report(a.leader_report, rows, d)
    print(json.dumps(out, indent=2, ensure_ascii=False) if a.json else markdown(out), end="" if not a.json else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
