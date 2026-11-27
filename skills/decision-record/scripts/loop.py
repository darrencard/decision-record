"""The Landing Loop record: one JSON file per bet, landing/<bet-slug>.json, shared by the loop's skills.

decision-record is step 01 (Decide). It reads the bet's landing brief and the `portfolio` key that
bet-portfolio-review wrote, and writes only its own key, `decisions`. Every other key is kept exactly as
it was found. It reads no key later than its own in the record order.

The `decisions` key carries the open decisions in the Product & Technology Leader Report's decision
format (`columns` and `rows`), so the report's decision slide reads them unchanged. Every figure carries
value, unit, source, window (from, to) and as_of, and is computed here from the decision log, never
written by the model. The words it uses are a decision's own: open, decided, dropped, past due. The
bet's status words belong to did-it-land and never appear here.

Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import declog  # noqa: E402
import landing_brief  # noqa: E402

VERSION = "0.3.0"
TOOL = f"decision-record {VERSION}"
SCHEMA = "landing-loop/1"
KEY = "decisions"
# The record order (Landing Loop contract). A skill reads only keys earlier than its own.
ORDER = ("portfolio", "decisions", "spec", "release", "cost", "evals", "landed", "signals", "postmortem", "board_qa")
READS = ("portfolio",)
MAX_RECORD_BYTES = 2_000_000


class RecordError(ValueError):
    """A record, brief or log that cannot be used. Nothing is written when this is raised."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path, folder: Path) -> str:
    """A path relative to the working folder, so the record reads the same on any machine."""
    return Path(os.path.relpath(path.resolve(), folder.resolve())).as_posix()


def path_for(folder: Path, bet: str) -> Path:
    return folder / "landing" / f"{bet}.json"


def load(path: Path, bet: str) -> dict[str, Any] | None:
    """The record as it stands, or None when there is none yet."""
    if not path.exists():
        return None
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise RecordError(f"{path} is over {MAX_RECORD_BYTES:,} bytes, so it is not a loop record.")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise RecordError(f"{path} is not valid JSON ({e}). Fix it or move it; it is never overwritten.") from None
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise RecordError(f"{path} is not a {SCHEMA} record. It is left as it is.")
    if record.get("bet") != bet:
        raise RecordError(f"{path} is the record for {record.get('bet')!r}, not {bet!r}. It is left as it is.")
    return record


def read_brief(path: Path) -> landing_brief.Brief:
    """The brief, through the vendored parser's own check. A brief with any part missing is refused whole."""
    try:
        return landing_brief.parse(path.read_text(encoding="utf-8"))
    except landing_brief.BriefError as e:
        raise RecordError(f"{path}: {e}") from None
    except OSError as e:
        raise RecordError(f"cannot read the brief {path} ({e.strerror}).") from None


def figure(value: Any, unit: str, source: str, window_from: str | None, window_to: str | None, as_of: str) -> dict[str, Any]:
    """One figure in the loop's shape. No figure without a source."""
    if not source:
        raise RecordError("a figure has no source. Every figure in the loop record needs one.")
    return {"value": value, "unit": unit, "source": source, "window": {"from": window_from, "to": window_to}, "as_of": as_of}


def tests_the_bar(r: declog.Record, brief: landing_brief.Brief) -> bool:
    """A decided record whose success signal names the brief's metric and bar is the call the bet is judged on."""
    signal = (r.success_signal or "").lower()
    return r.status == "decided" and brief.metric.lower() in signal and brief.bar_text.lower() in signal


def build(
    records: list[declog.Record],
    as_of: date,
    log_ref: dict[str, str],
    brief: landing_brief.Brief,
    portfolio: dict[str, Any] | None,
    usual_days: float | None = None,
    escalate_after: int = 14,
    illustrative: bool = False,
) -> dict[str, Any]:
    """The `decisions` key, from the log, the brief and the portfolio. Refused if the log is invalid."""
    errs = [f for f in declog.validate_log(records, as_of) if f.level == "error"]
    if errs:
        raise RecordError(f"the log has {len(errs)} invalid record(s), first {errs[0].record} {errs[0].rule}. Run record.py validate.")
    rows, problems = declog.leader_report_rows(records, as_of, usual_days, escalate_after)
    if problems:
        raise RecordError("; ".join(f"{f.record} {f.rule}: {f.message}" for f in problems))
    q = declog.open_queue(records, as_of, usual_days, escalate_after)
    day = as_of.isoformat()
    src = f"{TOOL}: counted from {log_ref['path']} (sha256 {log_ref['sha256'][:12]})"
    opened = sorted(r.opened for r in records if r.opened)
    start = opened[0] if opened else day

    figures: dict[str, Any] = {
        "open": figure(q["counts"]["open"], "decisions", src, start, day, day),
        "decided": figure(sum(1 for r in records if r.status == "decided"), "decisions", src, start, day, day),
        "past_due": figure(q["counts"]["past_due"], "decisions", src, start, day, day),
        "waiting_on_nobody": figure(q["counts"]["waiting_on_nobody"], "decisions", src, start, day, day),
    }
    gaps: list[str] = []
    ages = [i["days_waiting"] for i in q["items"] if i["days_waiting"] is not None]
    if ages:
        figures["oldest_open"] = figure(max(ages), "days", f"{src}; as_of minus the opened date", start, day, day)
    if q["usual_days_to_decide"] is not None:
        how = "set by the user" if usual_days is not None else "median days from opened to decided"
        figures["usual_days_to_decide"] = figure(q["usual_days_to_decide"], "days", f"{src}; {how}", start, day, day)
    else:
        gaps.append(f"usual time to decide not known: {q['usual_basis']}, so nothing is marked past due")
    for i in q["items"]:
        if i["days_waiting"] is not None:
            figures[f"days_waiting@{i['id']}"] = figure(i["days_waiting"], "days", f"{src}; as_of minus the opened date", i["opened"], day, day)
    for r in records:
        o, d = declog.parse_date(r.opened), declog.parse_date(r.date)
        if r.status == "decided" and o and d and d >= o:
            figures[f"days_to_decide@{r.id}"] = figure((d - o).days, "days", f"{src}; decided date minus the opened date", r.opened, r.date, day)

    tested_by = [r.id for r in records if tests_the_bar(r, brief)]
    if not tested_by:
        gaps.append(f"no decided record names the brief's bar ({brief.metric}, {brief.bar_text}) as its success signal")
    if portfolio is None:
        gaps.append("portfolio not read: run bet-portfolio-review first")

    decided = [
        {
            "id": r.id,
            "title": r.title,
            "chosen": r.chosen,
            "decided_by": r.decided_by,
            "date": r.date,
            "owner": r.owner,
            "review_by": r.review_by,
            "reversible": r.reversible,
            "success_signal": r.success_signal,
            "assumptions": list(r.assumptions),
            "evidence": r.evidence,
            "source": r.source,
        }
        for r in records
        if r.status == "decided"
    ]
    if q["items"]:
        first = next((i for i in q["items"] if i["past_due"]), q["items"][0])
        row = next(x for x in rows if x["id"] == first["id"])
        who = first["waiting_on"]
        ask = first["title"].rstrip(".")
        ask = ask[:1].lower() + ask[1:] if ask[1:2].islower() else ask
        next_step = f"{first['id']} waits on {who or 'nobody named'}: {ask}" + (f" by {row['deadline']}." if row["deadline"] else ".")
    else:
        who, next_step = None, "No open decisions on this bet."
    key: dict[str, Any] = {
        "tool": TOOL,
        "as_of": day,
        "log": dict(log_ref),
        "reads": {"brief": True, "portfolio": portfolio is not None},
        "columns": list(declog.LEADER_REPORT_COLUMNS + declog.LEADER_REPORT_EXTRA),
        "rows": rows,
        "decided": decided,
        "brief": {
            "metric": brief.metric,
            "bar": brief.bar_text,
            "better": "higher" if brief.higher_is_better else "lower",
            "by": brief.by,
            "decides": brief.decides,
            "tested_by": tested_by,
        },
        "figures": figures,
        "gaps": gaps,
        "next_step": next_step,
        "next_step_by": who,
        "next_in_loop": "Next in the loop, 02 Spec: run spec-auditor on the bet's spec against this brief before build starts.",
    }
    if illustrative:
        key["illustrative"] = True
    return key


def write(path: Path, record: dict[str, Any], key: dict[str, Any]) -> None:
    """Write the `decisions` key. Every other key is kept as found, in the record order."""
    head = {k: record[k] for k in ("schema", "bet", "brief") if k in record}
    merged = dict(record)
    merged[KEY] = key
    ordered = dict(head)
    for k in ORDER:
        if k in merged:
            ordered[k] = merged[k]
    for k, v in merged.items():
        ordered.setdefault(k, v)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(
    folder: Path,
    bet: str,
    log_path: Path,
    as_of: date,
    brief_path: Path | None = None,
    usual_days: float | None = None,
    escalate_after: int = 14,
    illustrative: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read the record, brief and log; write the `decisions` key. Returns (record, key)."""
    p = path_for(folder, bet)
    record = load(p, bet)
    if record is None:
        if brief_path is None:
            raise RecordError(f"there is no record at {p} yet. Pass --brief to start one.")
        record = {"schema": SCHEMA, "bet": bet, "brief": {"path": rel(brief_path, folder), "sha256": sha256(brief_path)}}
    stated = record.get("brief") or {}
    found = folder / stated.get("path", "")
    if brief_path is None:
        brief_path = found
    if not brief_path.is_file():
        raise RecordError(f"the brief {brief_path} is not there. The record names {stated.get('path')!r}, relative to {folder}.")
    if stated.get("sha256") and sha256(brief_path) != stated["sha256"]:
        raise RecordError(f"the brief {brief_path} changed after the record was opened (its sha256 no longer matches). Nothing is written.")
    brief = read_brief(brief_path)
    if not log_path.is_file():
        raise RecordError(f"there is no decision log at {log_path}.")
    records = declog.parse_log(log_path.read_text(encoding="utf-8"))
    log_ref = {"path": rel(log_path, folder), "sha256": sha256(log_path)}
    portfolio = record.get("portfolio")
    key = build(records, as_of, log_ref, brief, portfolio, usual_days, escalate_after, illustrative)
    write(p, record, key)
    return record, key
