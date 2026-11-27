#!/usr/bin/env python3
"""Regenerate the committed Acme sample: the log decisions.md, decision-record.html, decision-record.md,
leader-report-decisions.md and the decisions key of landing/quote-drafting.json, all read as of 2026-11-26.
Also the Decide-step view: decide-step/decisions.md and decide-step/open-decisions.md, as of 2026-07-27.

Inputs, all illustrative (Acme is an invented company): the canonical briefs in briefs/ (copied from the
landing-loop repo, unchanged), the decide call of 2026-07-27 and the spec review call of 2026-08-10 in
sources/, one draft per call in drafts/, and upstream/bet-portfolio-review.json, the landing-loop record
filtered to the keys decision-record reads (schema, bet, brief, portfolio), copied unchanged.

Each draft goes through record.py append on 2026-07-27, and each call made on 2026-08-10 through
record.py decide, so every record passes the same checks a real one does: the decider is named, and their
words are in the source on the date given. The log as it stood on 2026-07-27 (D-0004, the rollback
trigger, and D-0005, the model tier, still open) is kept and read as the Decide-step view, with no record
write. The record key is the full log read as of 2026-11-26. decision-record reads only brief and
portfolio, so a later as_of keeps record order. The same inputs give the same bytes.

Usage, from the repo root (Python 3.11 or later):
  python3 examples/acme/sample.py [--into DIR]
"""

from __future__ import annotations

import argparse
import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

if sys.version_info < (3, 11):  # noqa: UP036  (says so plainly on an older Python, instead of failing on an import)
    raise SystemExit("decision-record needs Python 3.11 or later; try python3.12.")

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "acme"
sys.path.insert(0, str(ROOT / "skills" / "decision-record" / "scripts"))

import open_decisions  # noqa: E402
import record  # noqa: E402

BET = "quote-drafting"
DECIDE_STEP = "2026-07-27"
AS_OF = "2026-11-26"
SOURCE = HERE / "sources" / "decide-call-2026-07-27.txt"
SPEC_REVIEW = HERE / "sources" / "spec-review-call-2026-08-10.txt"
OUTPUTS = (
    "decisions.md", "decision-record.html", "decision-record.md", "leader-report-decisions.md", f"landing/{BET}.json",
    "decide-step/decisions.md", "decide-step/open-decisions.md",
)  # fmt: skip

# The two calls made at the spec review of 2026-08-10, in the words of record.py decide.
SPEC_REVIEW_CALLS = (
    [
        "D-0004", "--decided-by", "Head of Product, Quoting squad", "--date", "2026-08-10",
        "--evidence", "My call: we roll back quote drafting when wrong-price quotes pass 2%.",
        "--chosen", "Roll back when wrong-price quotes pass 2%",
        "--decision", "Quote drafting rolls back when wrong-price quotes pass 2%. This closes the spec hold of 2026-08-03 on the rollback trigger.",
        "--owner", "Tech lead, Quoting squad", "--review-by", "2026-11-15", "--reversible", "yes",
        "--success-signal", "Wrong-price quotes stay below 2% to 2026-11-15 (illustrative).",
    ],
    [
        "D-0005", "--decided-by", "Tech lead, Quoting squad", "--date", "2026-08-10",
        "--evidence", "vendor-a/m drafts quotes in v1. Long drafts go to vendor-a/xl. That is my call.",
        "--chosen", "vendor-a/m",
        "--decision", "vendor-a/m drafts quotes in v1. Long drafts go to vendor-a/xl.",
        "--owner", "Tech lead, Quoting squad", "--review-by", "2026-11-15", "--reversible", "yes",
        "--success-signal", "Tokens per task within the brief's 9,000 budget to 2026-11-15 (illustrative).",
    ],
)  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--into", help="output folder (default examples/acme)")
    args = p.parse_args(argv)
    into = Path(args.into).resolve() if args.into else HERE
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copytree(HERE / "briefs", work / "briefs")
        (work / "landing").mkdir()
        shutil.copy(HERE / "upstream" / "bet-portfolio-review.json", work / "landing" / f"{BET}.json")
        log = work / "decisions.md"
        quiet = io.StringIO()
        for draft in sorted((HERE / "drafts").glob("*.json")):
            with contextlib.redirect_stdout(quiet):
                code = record.main(["append", "--draft", str(draft), "--source", str(SOURCE), "--as-of", DECIDE_STEP, "--log", str(log)])
            if code:
                raise SystemExit(f"sample: {draft.name} was refused:\n{quiet.getvalue()}")
        step = work / "decide-step"
        step.mkdir()
        shutil.copy(log, step / "decisions.md")
        read = io.StringIO()
        with contextlib.redirect_stdout(read):
            code = open_decisions.main(["--log", str(step / "decisions.md"), "--as-of", DECIDE_STEP])
        if code:
            raise SystemExit(f"sample: open_decisions.py refused the Decide-step log:\n{read.getvalue()}")
        (step / "open-decisions.md").write_text(read.getvalue(), encoding="utf-8")
        for call in SPEC_REVIEW_CALLS:
            args = ["decide", *call, "--source", str(SPEC_REVIEW), "--source-name", "Acme spec review call, 2026-08-10 (illustrative)"]
            with contextlib.redirect_stdout(quiet):
                code = record.main([*args, "--as-of", AS_OF, "--log", str(log)])
            if code:
                raise SystemExit(f"sample: record.py decide {call[0]} was refused:\n{quiet.getvalue()}")
        with contextlib.redirect_stdout(quiet):
            code = open_decisions.main(
                [
                    "--log", str(log), "--as-of", AS_OF,
                    "--loop", str(work), "--bet", BET, "--illustrative",
                    "--title", "Decisions on quote drafting",
                    "--html", str(work / "decision-record.html"),
                    "--md", str(work / "decision-record.md"),
                    "--leader-report", str(work / "leader-report-decisions.md"),
                ]
            )  # fmt: skip
        if code:
            raise SystemExit(f"sample: open_decisions.py refused:\n{quiet.getvalue()}")
        for name in OUTPUTS:
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(work / name, into / name)
    print(f"sample: wrote {', '.join(OUTPUTS)} to {into}")


if __name__ == "__main__":
    main()
