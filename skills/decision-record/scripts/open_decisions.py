"""List open decisions with days waiting and on whom, and read follow-through.

    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --json
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --usual-days 10
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --leader-report run/decisions.md
    python3 scripts/open_decisions.py --log decisions.md --as-of YYYY-MM-DD --loop . --bet quote-drafting --html decisions.html

--loop writes the `decisions` key of landing/<bet>.json in that folder (Landing Loop step 01, Decide),
reading the bet's landing brief and the `portfolio` key, and keeping every other key as it was.
--html and --md render that key as one page in the Leader Report style and its Markdown twin.

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

if sys.version_info < (3, 11):  # noqa: UP036  (say so plainly on an old Python, before reading or writing anything)
    sys.exit("decision-record needs Python 3.11 or later; try python3.12.")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import declog  # noqa: E402
import loop  # noqa: E402
import render_html  # noqa: E402


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
        lines += [f"Usual time to decide: not known ({q['usual_basis']}), so nothing is marked as waiting longer than usual.", ""]
    if q["counts"]["escalated"]:
        lines += [f"Escalate: waiting more than {q['escalate_after_days']} days longer than usual with nobody named to make the call.", ""]
    if q["items"]:
        lines += ["| Id | Decision needed | Days waiting | Waiting on | Flag |", "|---|---|---|---|---|"]
        for i in q["items"]:
            flag = ", ".join(w for w, on in (("escalate", i["escalated"]), ("past due", i["past_due"]), ("longer than usual", i["waiting_long"] and not i["escalated"])) if on)
            days = "no date" if i["days_waiting"] is None else str(i["days_waiting"])
            lines.append(f"| {i['id']} | {i['title']} | {days} | {i['waiting_on'] or 'nobody named'} | {flag} |")
        lines.append("")
    lines += [f"## Follow-through as of {ft['as_of']}", ""]
    rate = "no rate yet" if ft["follow_through_rate_pct"] is None else f"{ft['follow_through_rate_pct']}%"
    counts = f"worked {ft['worked']} · pending {ft['pending']} · missed {ft['missed']} · not yet read {ft['not_yet_read']}"
    lines.append(f"Follow-through: {rate} ({ft['rate_basis']}). {counts}.")
    if ft["missed_rows"]:
        lines += ["", "Missed: " + "; ".join(f"{r['id']} {r['title']} (owner: {r['owner'] or 'none'})" for r in ft["missed_rows"])]
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
    p.add_argument("--escalate-after", type=int, default=14, help="Days longer than usual, with nobody named, before a call escalates.")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--leader-report",
        type=Path,
        metavar="FILE",
        help="Also write the open decisions in the Leader Report's decision format (.md or .csv), for intake.py import --decisions.",
    )
    p.add_argument("--loop", type=Path, metavar="FOLDER", help="Write the decisions key of FOLDER/landing/<bet>.json.")
    p.add_argument("--bet", help="The bet's slug, the record's file name (with --loop).")
    p.add_argument("--brief", type=Path, help="The bet's landing brief, to start a record that does not exist yet (with --loop).")
    p.add_argument("--html", type=Path, metavar="FILE", help="Render the decisions key as one HTML page (with --loop).")
    p.add_argument("--md", type=Path, metavar="FILE", help="Its Markdown twin (with --loop).")
    p.add_argument("--title", help="The page title. Default: the bet's slug, as words.")
    p.add_argument("--illustrative", action="store_true", help="Mark the record and page illustrative (sample data).")
    a = p.parse_args(argv)
    if (a.html or a.md or a.bet or a.brief) and not a.loop:
        raise SystemExit("--bet, --brief, --html and --md go with --loop FOLDER.")
    if a.loop and not a.bet:
        raise SystemExit("--loop needs --bet, the bet's slug (its record is landing/<bet>.json).")
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
    if a.loop:
        try:
            record, key = loop.run(a.loop, a.bet, a.log, d, a.brief, a.usual_days, a.escalate_after, a.illustrative)
        except loop.RecordError as err:
            print(f"refused: {err}", file=sys.stderr)
            return 2
        title = a.title or f"Decisions: {a.bet.replace('-', ' ').capitalize()}"
        if a.html:
            a.html.write_text(render_html.page(key, record, title), encoding="utf-8")
        if a.md:
            a.md.write_text(render_html.markdown(key, record, title), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False) if a.json else markdown(out), end="" if not a.json else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
