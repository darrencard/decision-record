#!/usr/bin/env python3
"""Regenerate the committed Acme sample: decisions.md, decision-record.html, decision-record.md,
leader-report-decisions.md and the decisions key of landing/quote-drafting.json.

Inputs, all illustrative (Acme is an invented company): the canonical briefs in briefs/ (copied from the
landing-loop repo, unchanged), the decide call of 2026-07-27 in sources/, one draft per call in drafts/,
and upstream/bet-portfolio-review.json, the landing-loop record filtered to the keys decision-record reads
(schema, bet, brief, portfolio), copied unchanged.

Each draft goes through record.py append, so every record passes the same checks a real one does: the
decider is named, and their words are in the source on the date given. The same inputs give the same bytes.

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
    raise SystemExit("decision-record needs Python 3.11 or later.")

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "acme"
sys.path.insert(0, str(ROOT / "skills" / "decision-record" / "scripts"))

import open_decisions  # noqa: E402
import record  # noqa: E402

BET = "quote-drafting"
AS_OF = "2026-07-27"
SOURCE = HERE / "sources" / "decide-call-2026-07-27.txt"
OUTPUTS = ("decisions.md", "decision-record.html", "decision-record.md", "leader-report-decisions.md", f"landing/{BET}.json")


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
        for name in OUTPUTS:
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(work / name, into / name)
    print(f"sample: wrote {', '.join(OUTPUTS)} to {into}")


if __name__ == "__main__":
    main()
