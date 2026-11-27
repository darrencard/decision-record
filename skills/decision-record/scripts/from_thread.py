#!/usr/bin/env python3
"""Turn a thread export into a source file the other scripts read, with no retyping.

Usage:
  python3 scripts/from_thread.py --slack history.json [--users users.json] --out run/source.txt
  python3 scripts/from_thread.py --linear comments.json --out run/source.txt
  python3 scripts/from_thread.py --csv thread.csv --out run/source.txt

Live first: save what the Slack or Linear connector (or API) returns, as it stands, and point this at it.
  --slack   conversations.history or conversations.replies results ({"messages": [...]}): each message's
            ts, text, and user_name, user_profile.real_name or user. A bare user id is looked up in
            --users (users.list results, {"members": [...]}) and kept as the id when it is not there.
  --linear  the Linear connector's list_comments result, or the GraphQL API's
            ({"comments": [...]} or {"data": {"comments": {"nodes": [...]}}}): body, createdAt, user.name.
CSV is the fallback for anything else (a meeting tool, email, a chat app): columns when, who, text,
with when as YYYY-MM-DD or YYYY-MM-DD HH:MM.

Each message becomes one line, oldest first: `[YYYY-MM-DD HH:MM] Name: text`, times in UTC. Newlines inside
a message are collapsed, so a message can never pose as a second speaker. No Leader Report collector reads
thread text (they read metrics, trackers and document lists), so this script is decision-record's own.

This script reads files and writes a file. It makes no network calls. Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if sys.version_info < (3, 11):  # noqa: UP036  (say so plainly on an old Python, before reading or writing anything)
    sys.exit("decision-record needs Python 3.11 or later; try python3.12.")

MAX_BYTES = 20_000_000


class ExportError(ValueError):
    """An export that cannot be read. Nothing is written."""


def one_line(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def load_json(path: Path) -> Any:
    if path.stat().st_size > MAX_BYTES:
        raise ExportError(f"{path} is over {MAX_BYTES:,} bytes. Split the export.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ExportError(f"{path} is not valid JSON ({e}).") from None


def from_slack(data: Any, users: dict[str, str]) -> list[tuple[str, str, str]]:
    msgs = data.get("messages") if isinstance(data, dict) else data
    if not isinstance(msgs, list):
        raise ExportError('a Slack export holds {"messages": [...]}. Save the connector or API result as it stands.')
    out = []
    for m in msgs:
        if not isinstance(m, dict) or not m.get("text") or m.get("subtype") in ("channel_join", "channel_leave"):
            continue
        try:
            when = datetime.fromtimestamp(float(m["ts"]), UTC).strftime("%Y-%m-%d %H:%M")
        except (KeyError, TypeError, ValueError):
            raise ExportError(f"a Slack message has no readable ts: {str(m)[:80]}") from None
        uid = m.get("user") or ""
        who = m.get("user_name") or (m.get("user_profile") or {}).get("real_name") or users.get(uid) or uid or "unknown"
        out.append((when, one_line(who), one_line(m["text"])))
    return out


def slack_users(data: Any) -> dict[str, str]:
    members = data.get("members") if isinstance(data, dict) else None
    if not isinstance(members, list):
        raise ExportError('--users holds users.list results ({"members": [...]}).')
    return {m["id"]: (m.get("real_name") or (m.get("profile") or {}).get("real_name") or m.get("name") or m["id"]) for m in members if isinstance(m, dict) and "id" in m}


def from_linear(data: Any) -> list[tuple[str, str, str]]:
    nodes = None
    if isinstance(data, dict):
        nodes = data.get("comments")
        if nodes is None:
            nodes = ((data.get("data") or {}).get("comments") or {}).get("nodes")
    if not isinstance(nodes, list):
        raise ExportError('a Linear export holds {"comments": [...]} or {"data": {"comments": {"nodes": [...]}}}.')
    out = []
    for c in nodes:
        if not isinstance(c, dict) or not c.get("body"):
            continue
        try:
            when = datetime.fromisoformat(str(c["createdAt"]).replace("Z", "+00:00")).astimezone(UTC).strftime("%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            raise ExportError(f"a Linear comment has no readable createdAt: {str(c)[:80]}") from None
        user = c.get("user") if isinstance(c.get("user"), dict) else {}
        out.append((when, one_line(user.get("name") or user.get("displayName") or "unknown"), one_line(c["body"])))
    return out


def from_csv(path: Path) -> list[tuple[str, str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or not {"when", "who", "text"} <= set(rows[0]):
        raise ExportError(f"{path} needs the columns when, who, text.")
    out = []
    for n, r in enumerate(rows, start=2):
        when = (r["when"] or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?", when):
            raise ExportError(f"{path} line {n}: when is {when!r}. Write YYYY-MM-DD or YYYY-MM-DD HH:MM.")
        if (r["text"] or "").strip():
            out.append((when, one_line(r["who"]) or "unknown", one_line(r["text"])))
    return out


def source_text(messages: list[tuple[str, str, str]], label: str) -> str:
    lines = [f"From {label}, times in UTC."] + [f"[{w}] {who}: {text}" for w, who, text in sorted(messages, key=lambda m: m[0])]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--slack", type=Path)
    g.add_argument("--linear", type=Path)
    g.add_argument("--csv", type=Path)
    p.add_argument("--users", type=Path, help="Slack users.list results, to turn user ids into names.")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        if a.slack:
            msgs, label = from_slack(load_json(a.slack), slack_users(load_json(a.users)) if a.users else {}), f"Slack export {a.slack.name}"
        elif a.linear:
            msgs, label = from_linear(load_json(a.linear)), f"Linear comments {a.linear.name}"
        else:
            msgs, label = from_csv(a.csv), f"CSV {a.csv.name}"
    except ExportError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    a.out.write_text(source_text(msgs, label), encoding="utf-8")
    print(f"from_thread: wrote {len(msgs)} message(s) to {a.out}. Next: python3 scripts/scan.py {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
