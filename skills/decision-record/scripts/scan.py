"""Read a Slack thread, meeting notes or a transcript and list what a record can quote.

Prints JSON: every utterance with its line number and speaker, the people who
spoke, any ISO dates in the text, and the lines that sound like a call being made
or a question still open. It finds candidates only. It never decides that a
decision was made: that takes a named decider, and the validator checks it.

    python3 scripts/scan.py thread.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import declog  # noqa: E402

DECISION_CUES = re.compile(
    r"\b(decided|decision is|my call|final call|we'?ll go with|let'?s go with|going with|agreed|approve[sd]?|"
    r"sign(?:ed)? off|we are doing|we're doing|ship it|go ahead|confirmed|locking|locked)\b",
    re.IGNORECASE,
)
DEFER_CUES = re.compile(
    r"\b(pick (?:this|it) up|next week|park(?:ed)?|revisit|not decided|no decision|tbd|need(?:s)? (?:a|to) (?:decide|call)|"
    r"come back|follow up|circle back|until we (?:know|hear|see))\b",
    re.IGNORECASE,
)


def scan(text: str) -> dict:
    utt = declog.parse_source(text)
    cues = []
    for u in utt:
        tags = []
        if DECISION_CUES.search(u["text"]):
            tags.append("decision-language")
        if DEFER_CUES.search(u["text"]):
            tags.append("deferred-language")
        if u["text"].rstrip().endswith("?"):
            tags.append("question")
        if tags:
            cues.append({"line": u["line"], "speaker": u["speaker"], "tags": tags, "text": u["text"]})
    return {
        "utterances": len(utt),
        "speakers": declog.speakers(utt),
        "dates": sorted(set(declog.DATE_IN_TEXT.findall(text))),
        "cues": cues,
        "lines": utt,
        "note": "Candidates only. Decision language is not a decision: a record is decided only with a named decider and their line as evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", type=Path)
    args = p.parse_args(argv)
    print(json.dumps(scan(args.source.read_text(encoding="utf-8")), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
