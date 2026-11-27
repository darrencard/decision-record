#!/usr/bin/env python3
"""Regenerate the committed Acme sample: decisions.md, decision-record.html, decision-record.md,
leader-report-decisions.md and the decisions key of landing/quote-drafting.json, all as of 2026-07-27,
the Decide step. Then the same log read later: later/decisions.md and later/open-decisions.md.

Inputs, all illustrative (Acme is an invented company): the canonical briefs in briefs/ (copied from the
landing-loop repo, unchanged), the decide call of 2026-07-27 in sources/, one draft per call in drafts/,
and upstream/bet-portfolio-review.json, the landing-loop record filtered to the keys decision-record reads
(schema, bet, brief, portfolio), copied unchanged.

Each draft goes through record.py append, so every record passes the same checks a real one does: the
decider is named, and their words are in the source on the date given. The record's decisions key stays as
of 2026-07-27, so it comes before 02 Spec in record order; there D-0004 (rollback trigger) and D-0005 (model
tier) are open. The later read records both calls from the spec review call of 2026-08-10 with record.py
decide, then reads the log as of 2026-11-26. It writes no key. The same inputs give the same bytes.

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
AS_OF = "2026-07-27"
LATER = "2026-11-26"
SOURCE = HERE / "sources" / "decide-call-2026-07-27.txt"
SPEC_REVIEW = HERE / "sources" / "spec-review-call-2026-08-10.txt"
OUTPUTS = (
    "decisions.md", "decision-record.html", "decision-record.md", "leader-report-decisions.md", f"landing/{BET}.json",
    "later/decisions.md", "later/open-decisions.md",
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
                code = record.main(["append", "--draft", str(draft), "--source", str(SOURCE), "--as-of", AS_OF, "--log", str(log)])
            if code:
                raise SystemExit(f"sample: {draft.name} was refused:\n{quiet.getvalue()}")
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
        later = work / "later"
        later.mkdir()
        shutil.copy(log, later / "decisions.md")
        for call in SPEC_REVIEW_CALLS:
            args = ["decide", *call, "--source", str(SPEC_REVIEW), "--source-name", "Acme spec review call, 2026-08-10 (illustrative)"]
            with contextlib.redirect_stdout(quiet):
                code = record.main([*args, "--as-of", LATER, "--log", str(later / "decisions.md")])
            if code:
                raise SystemExit(f"sample: record.py decide {call[0]} was refused:\n{quiet.getvalue()}")
        read = io.StringIO()
        with contextlib.redirect_stdout(read):
            code = open_decisions.main(["--log", str(later / "decisions.md"), "--as-of", LATER])
        if code:
            raise SystemExit(f"sample: open_decisions.py refused the later log:\n{read.getvalue()}")
        (later / "open-decisions.md").write_text(read.getvalue(), encoding="utf-8")
        for name in OUTPUTS:
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(work / name, into / name)
    print(f"sample: wrote {', '.join(OUTPUTS)} to {into}")


if __name__ == "__main__":
    main()
