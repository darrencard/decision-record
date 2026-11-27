"""The `decisions` key as one self-contained HTML page, in the Leader Report style guide and the Landing Loop's one
visual family, and its Markdown twin.

The page takes the report's whole stylesheet from its template (assets/vendor/template.html, vendored byte-identical
at a pinned commit) and draws its picture with svgkit (scripts/vendor/svgkit.py, vendored byte-identical from
landing-loop). Only a few rules for this page's layout are added.

It reads top down for someone who has never seen the loop: the shared header, the verdict as the heading, the days
each decision took as scorecard rows (name, plan and actual bars, `28 DAYS`, the decider in brass), then one thing
to do next. The rows follow the scorecard grammar (svgkit 1.2.0): HTML rows split by hairlines, Geist Mono 12px for
labels and figures, Geist 14px for names, fixed-height bars with no text in them. The plan is the log's usual time
to decide, printed once in the frame head ("PLAN 14 DAYS"); the part of a bar past it is hatched, because hatching
means over plan and nothing else.
Each call follows in two columns, then what the record read. The evidence ledger and the engineering detail (key
names, the log's hash, model ids, the decider's exact words) sit in folds. Public copy uses plain words: project,
target, landing brief (defined at first use), when you would undo it, the large model.

Colour means one thing each: brass for a person's call (who decided, who a call waits on), grey for the plan and the record's own
marks. There is no status colour on this page: a decision is open or decided, and the project's status words belong
to did-it-land. The picture draws only figures the page prints, and its aria-label states the answer.

Nothing is loaded from the network, nothing depends on the clock or the machine, and every piece of text from a
source is escaped.

Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

import svgkit as sk  # noqa: E402  (vendored, unchanged; see VENDORED.json)

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "vendor" / "template.html"
STYLE = re.compile(r"<style>(.*?)</style>", re.S)
NAME = "Decision record"  # the page prints its plain name; the code name sits in the engineers' fold
MIN_FONT_PX = 11  # no text on the page prints smaller, at any width

# Layout for this page only. Everything else comes from the template's stylesheet and svgkit.CSS. The template paints
# selection and the focus ring green, a status colour; this page sets both to ink.
PAGE_CSS = """
::selection{background:var(--t1);color:var(--bg)}
:focus-visible{outline-color:var(--t1)}
main.solo{margin-left:0}
.solo .slide{min-height:0}
.solo .slide.cover{min-height:0;padding-top:40px;padding-bottom:48px;justify-content:flex-start}
.solo h1{font-size:clamp(34px,4.6vw,60px);line-height:1;letter-spacing:-.04em;max-width:22ch;margin-bottom:20px}
.solo .lede{margin-bottom:28px}
.solo .lede b{color:var(--t1);font-weight:500}
.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px 48px;align-items:start;margin-top:32px}
.side{display:grid;gap:24px}
.next{display:grid;gap:10px;border:1px solid var(--brass);border-radius:12px;padding:20px 22px;background:var(--brass-bg)}
.next>b{font:400 11px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--brass)}
.next p{margin:0;font-size:16px;line-height:1.5;color:var(--t1)}
.next .whom{display:flex;flex-wrap:wrap;gap:4px 24px;font:400 11.5px/18px var(--mono);color:var(--brass)}
.next .whom i{font-style:normal;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);margin-right:8px}
.next .whom .d{color:var(--t2)}
.figs{margin:0;display:grid}
.figs>div{display:grid;grid-template-columns:120px minmax(0,1fr);gap:4px 16px;border-top:1px solid var(--line);padding:10px 0}
.figs dt{font:400 11px/22px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.figs dd{margin:0;font-size:13.5px;line-height:1.55;color:var(--t2)}
.figs dd b{color:var(--t1);font-weight:500}
.figs ul{margin:0;padding-left:16px}
.who{color:var(--brass);font-family:var(--mono);font-size:12.5px}
.calls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--s1)}
.call{padding:20px 24px 14px;box-shadow:-1px 0 0 var(--line),0 -1px 0 var(--line)}
.call h3{margin:0 0 10px;font:600 18px/1.25 var(--display);text-transform:none;letter-spacing:-.02em;color:var(--t1)}
.call h3 .rk{display:block;font:400 11px/16px var(--mono);letter-spacing:.1em;color:var(--t3);margin-bottom:4px}
.call .figs>div:first-child{border-top:0}
.call details{margin-top:4px}
.flag{font:400 12px/16px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--t1);margin-left:8px}
.ask{font:600 21px/1.25 var(--display);letter-spacing:-.02em;color:var(--t1);margin:28px 0 6px}
.ask:first-of-type{margin-top:0}
.rec{color:var(--t2);font-size:13.5px;margin:0}
.quote{margin:8px 0 0;font-size:13px;line-height:1.55;color:var(--t2)}
.quote span{display:block;font:400 11px/18px var(--mono);color:var(--t3)}
.solo details{margin-top:20px}
.solo details .tablewrap{margin-top:12px}
.note{max-width:80ch;font-size:12.5px;line-height:1.6;color:var(--t2);margin:12px 0 0}
.eng td{font-size:12px;vertical-align:top}
.foot{max-width:1120px;margin:0 auto;padding:28px 40px 64px;color:var(--t3);font-size:12px}
@media (max-width:1100px){.cols{grid-template-columns:minmax(0,1fr)}}
@media (max-width:980px){.foot{padding:24px 16px 48px}.solo .slide.cover{padding-top:24px}.calls{grid-template-columns:minmax(0,1fr)}}
@media (max-width:560px){.figs>div{grid-template-columns:1fr;gap:0}.call{padding:16px 16px 12px}}
"""

NUMBER_WORDS = ("No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve")

# The record's words in the page's words. The record and the log keep the original text; the decider's exact words
# are never changed, and print in a fold.
WORDS = (
    (r"\b([Ss])et the rollback trigger for\b", r"\1et when to undo"),
    (r"\bthe rollback trigger\b", "when to undo it"),
    (r"\bRoll back\b", "Undo"),
    (r"\brolls back\b", "is undone"),
    (r"\broll back\b", "undo"),
    (r"\bChoose the model tier for\b", "Choose the AI model for"),
    (r"\bvendor-a/xl\b", "the large model"),
    (r"\bvendor-a/m\b", "the mid-size model"),
    (r"\b(\d[\d,]*) tokens per task\b", r"AI usage of \1 per task"),
    (r"\b[Tt]okens per task\b", "AI usage per task"),
    (r"\bthe brief's\b", "the landing brief's"),
    (r"\bspec hold\b", "build plan hold"),
    (r"\bthis bet\b", "this project"),
    (r"\bthe bet\b", "the project"),
    (r"\bbets\b", "projects"),
    (r"\bbet\b", "project"),
    (r"\bthe bar\b", "the target"),
)

# The ledger's figure names, in plain words. The key keeps its names; they print in the engineers' fold.
FIGURE_NAMES = {
    "open": "Open",
    "decided": "Decided",
    "waiting_long": "Waiting longer than usual",
    "past_due": "Past their decide-by date",
    "waiting_on_nobody": "Waiting on nobody",
    "usual_days_to_decide": "Usual time to decide (median)",
    "days_to_decide": "Days to decide",
    "days_waiting": "Days waiting",
}


def e(text: Any) -> str:
    return html.escape(str(text), quote=True)


def plain(text: str) -> str:
    """The record's words in the page's words."""
    for pattern, to in WORDS:
        text = re.sub(pattern, to, text)
    return text[:1].upper() + text[1:] if text[:1].islower() and text.startswith("the ") else text


def figure_name(name: str) -> str:
    base, _, rid = name.partition("@")
    return f"{FIGURE_NAMES.get(base, base)}, {rid}" if rid else FIGURE_NAMES.get(base, base)


def portfolio_parts(p: dict[str, Any]) -> list[str]:
    """The portfolio review's rank and readiness, in plain words: 'rank 4 of 8', 'readiness 14 of 14 points'."""
    parts = []
    rank, score = p.get("rank"), p.get("brief_score")
    if isinstance(rank, dict) and "value" in rank:
        m = re.match(r"rank of (\d+)", str(rank.get("unit", "")))
        parts.append(f"rank {rank['value']} of {m.group(1)}" if m else f"rank {rank['value']}")
    if isinstance(score, dict) and "value" in score:
        m = re.match(r"points of (\d+)", str(score.get("unit", "")))
        parts.append(f"readiness {score['value']} of {m.group(1)} points" if m else f"readiness {score['value']}")
    return parts


def stylesheet() -> str:
    """The report template's whole stylesheet, fonts included."""
    try:
        found = STYLE.search(TEMPLATE.read_text(encoding="utf-8"))
    except OSError:
        found = None
    return found.group(1) if found else ""


def floor_fonts(css: str) -> str:
    """Every font size in the page's CSS at MIN_FONT_PX or more. The vendored template and svgkit stay byte-identical;
    their smaller label sizes are raised here, as the page is written. A line height (after the slash) is left alone."""

    def raise_px(decl: re.Match[str]) -> str:
        return re.sub(r"(?<![/\d.])(\d+(?:\.\d+)?)px", lambda m: f"{MIN_FONT_PX}px" if float(m.group(1)) < MIN_FONT_PX else m.group(0), decl.group(0))

    return re.sub(r"font(?:-size)?:[^;}]*", raise_px, css)


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def count_word(n: int) -> str:
    return NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)


def and_join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def usual(key: dict[str, Any]) -> float | None:
    f = key["figures"].get("usual_days_to_decide")
    return f["value"] if f else None


def late_rows(key: dict[str, Any]) -> list[dict[str, Any]]:
    """Open decisions waiting longer than the log's usual time to decide."""
    f, u = key["figures"], usual(key)
    return [r for r in key["rows"] if u is not None and f"days_waiting@{r['id']}" in f and r["days_waiting"] > u]


def lede(key: dict[str, Any]) -> str:
    """'3 decided, 2 open. 1 waiting longer than usual: D-0004 has waited 14 days on Lead, Quoting squad, against a usual 7.'

    "Longer than usual" is against the log's usual time to decide. "Past due" is only a decide-by date that has passed."""
    f = key["figures"]
    out = f"{f['decided']['value']} decided, {f['open']['value']} open."
    late = late_rows(key)
    if late:
        r = late[0]
        who = r["owner"] or "nobody named"
        out += f" {len(late)} waiting longer than usual: {r['id']} has waited {plural(r['days_waiting'], 'day')} on {who}, against a usual {f['usual_days_to_decide']['value']:g}."
    slow = slow_calls(key)
    if slow:
        calls = ", ".join(f"{i} ({plural(n, 'day')})" for i, n in slow)
        out += f" {len(slow)} took longer than the usual {f['usual_days_to_decide']['value']:g} days to decide: {calls}."
    due = [r for r in key["rows"] if r["deadline"] and r["deadline"] < key["as_of"]]
    if due:
        r = due[0]
        out += f" {len(due)} past due: {r['id']} was to be decided by {r['deadline']}."
    return out


def verdict(key: dict[str, Any]) -> str:
    """The heading: how many calls are made, how many wait, and the one thing that stands out."""
    n_open, n_done = len(key["rows"]), len(key["decided"])
    total = n_open + n_done
    if not total:
        return "No decisions recorded yet."
    if not n_open:
        parts = [f"All {count_word(total).lower()} decisions are made; none is open." if total > 1 else "The one decision is made."]
    else:
        parts = [f"{count_word(n_open)} of {count_word(total).lower()} decisions {'is' if n_open == 1 else 'are'} still open."]
    due = [r for r in key["rows"] if r["deadline"] and r["deadline"] < key["as_of"]]
    late = late_rows(key)
    slow = slow_calls(key)
    if due:
        parts.append(f"{due[0]['id']} is past its decide-by date.")
    elif late:
        parts.append(f"{late[0]['id']} has waited longer than usual on {late[0]['owner'] or 'nobody named'}.")
    elif slow:
        parts.append(f"{count_word(len(slow))} took longer than usual to decide.")
    return " ".join(parts)


def figure_text(fig: dict[str, Any]) -> str:
    v = fig["value"]
    return f"{v:g} {fig['unit']}" if isinstance(v, float) else f"{v} {fig['unit']}"


def took(key: dict[str, Any], d: dict[str, Any]) -> str:
    """', 28 days after it was opened, longer than the usual 14': a decision's history, from the figures."""
    f = key["figures"]
    fig = f.get(f"days_to_decide@{d['id']}")
    if not fig:
        return ""
    out = f", {plural(fig['value'], 'day')} after it was opened"
    u = f.get("usual_days_to_decide")
    if u and fig["value"] > u["value"]:
        out += f", longer than the usual {u['value']:g}"
    return out


def slow_calls(key: dict[str, Any]) -> list[tuple[str, int]]:
    """Decided records that took longer than the usual time to decide, slowest first."""
    f = key["figures"]
    u = f.get("usual_days_to_decide")
    if not u:
        return []
    slow = [(d["id"], f[f"days_to_decide@{d['id']}"]["value"]) for d in key["decided"] if f"days_to_decide@{d['id']}" in f]
    return sorted([x for x in slow if x[1] > u["value"]], key=lambda x: (-x[1], x[0]))


def next_step(key: dict[str, Any]) -> tuple[str, str, str, str]:
    """(the step, who, their role, when): the open call that waits longest on a person, or else the next review."""
    if key["rows"]:
        m = re.match(r"^(D-\d+) waits on (.+?): (.*?)(?: by (\d{4}-\d{2}-\d{2}))?\.$", key["next_step"])
        if m:
            return f"Decide {m.group(1)}: {plain(m.group(3))}.", key.get("next_step_by") or "nobody named", "Waiting on", m.group(4) or "no date set"
        return plain(key["next_step"]), key.get("next_step_by") or "nobody named", "Waiting on", "no date set"
    reviews = sorted({d["review_by"] for d in key["decided"] if d["review_by"]})
    if not reviews:
        return "Nothing waits on anyone: no decision is open and none has a review date.", key["brief"]["decides"], "Decides", "no date set"
    first = reviews[0]
    ids = [d["id"] for d in key["decided"] if d["review_by"] == first]
    what = f"all {count_word(len(ids)).lower()} decisions" if len(ids) == len(key["decided"]) and len(ids) > 1 else and_join(ids)
    when = f"was due {first}" if first < key["as_of"] else f"review by {first}"
    return f"Review {what} against {'its' if len(ids) == 1 else 'their'} success signal{'' if len(ids) == 1 else 's'}.", key["brief"]["decides"], "Decides", when


# The signature picture: one row per decision, raised to decided, the person's call in brass.


def _day(text: str) -> int:
    return dt.date.fromisoformat(text).toordinal()


def spans(key: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per decision with a known opened date: decided calls first in log order, then open ones."""
    f, u = key["figures"], usual(key)
    out = []
    for d in key["decided"]:
        fig = f.get(f"days_to_decide@{d['id']}")
        if fig:
            out.append(
                {
                    "id": d["id"],
                    "what": plain(d["chosen"] or d["title"]),
                    "title": plain(d["title"]),
                    "who": d["decided_by"],
                    "from": fig["window"]["from"],
                    "to": fig["window"]["to"],
                    "days": fig["value"],
                    "open": False,
                    "slow": u is not None and fig["value"] > u,
                }
            )
    for r in key["rows"]:
        fig = f.get(f"days_waiting@{r['id']}")
        if fig:
            out.append(
                {
                    "id": r["id"],
                    "what": plain(r["ask"]),
                    "title": plain(r["ask"]),
                    "who": r["owner"] or "nobody named",
                    "from": fig["window"]["from"],
                    "to": fig["window"]["to"],
                    "days": fig["value"],
                    "open": True,
                    "slow": u is not None and fig["value"] > u,
                }
            )
    return out


def days_rows(key: dict[str, Any]) -> str:
    """One row per decision: its name, the plan (the usual days) above the days it took, `28 DAYS`, and the person in
    brass. Bars share one scale, the longest row; the part past the plan is hatched."""
    rows = spans(key)
    u = usual(key)
    top = max([s["days"] for s in rows] + [u or 0])
    out = []
    for i, s in enumerate(rows, start=1):
        picture = sk.paired_bars(u, s["days"], top=top, hatch_id=f"dr-over-{i}") if u is not None else sk.share_bar(s["days"], top)
        days = f"{plural(s['days'], 'day').upper()}{' WAITING' if s['open'] else ''}"
        word = (sk.check_word("open", ink=True) if s["open"] else "") + sk.person_call(s["who"])
        out.append(sk.sc_row(s["title"], picture=picture, figure=sk.figure_line(days), word=word))
    plan = f"plan {u:g} days" if u is not None else "days"
    key_ = sk.legend("plan", plan) + sk.legend("actual", "took") + sk.legend("over", "over plan") if u is not None else ""
    return sk.sc_frame(
        out,
        label=timeline_label(key, rows),
        title="Days to decide",
        head=["Decision", "", "Days", "Decided by" if not key["rows"] else "Decided by or waiting on"],
        legend=key_,
        caption=caption(key),
        illustrative=bool(key.get("illustrative")),
    )


def timeline_label(key: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """The picture's answer in one sentence."""
    slow = [s for s in rows if s["slow"] and not s["open"]]
    waiting = [s for s in rows if s["open"]]
    u = usual(key)
    head = f"{count_word(len(rows))} decisions from the day each was raised to the day a named person made it"
    if waiting:
        head += f"; {and_join([s['id'] for s in waiting])} still {'waits' if len(waiting) == 1 else 'wait'}"
    if slow and u is not None:
        took_ = and_join([f"{s['id']} took {plural(s['days'], 'day')}" for s in slow])
        head += f"; {took_}, longer than the usual {u:g}"
    return head + "."


def caption(key: dict[str, Any]) -> str:
    u = usual(key)
    out = "Each row is one decision, from the day it was raised to the day a named person made it."
    if u is not None:
        out += f" Grey is the plan, {u:g} days, the median for this log; ink is the days it took; the part past the plan is hatched."
    if key["rows"]:
        out += " An open row is still waiting on the person named."
    return out


# Sections


def next_box(key: dict[str, Any]) -> str:
    step, who, role, when = next_step(key)
    return (
        f'<div class="next"><b>What to do next</b><p>{e(step)}</p>'
        f'<span class="whom"><span class="o"><i>{e(role)}</i>{e(who)}</span><span class="d"><i>When</i>{e(when)}</span></span></div>'
    )


def glance(key: dict[str, Any]) -> str:
    f = key["figures"]
    rows = [("Decided", f"<b>{f['decided']['value']}</b> decisions"), ("Open", f"<b>{f['open']['value']}</b> waiting on a named person")]
    if "usual_days_to_decide" in f:
        rows.append(("Usual time", f"<b>{f['usual_days_to_decide']['value']:g} days</b> from raised to decided, the median"))
    slow = slow_calls(key)
    if slow:
        rows.append(("Longest", f"<b>{plural(slow[0][1], 'day')}</b> for {e(slow[0][0])}"))
    rows.append(("Past due", f"<b>{f['past_due']['value']}</b> past their decide-by date"))
    return '<dl class="figs">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>"


def open_block(r: dict[str, Any], fig: dict[str, Any] | None) -> str:
    """One open decision, as the report's decision slide draws it: options as rows, the deadline in brass."""
    options = [o for o in (r["options"] or "").split(" or ") if o]
    rows = "".join(f'<div><span class="dc-k">Option {chr(65 + i)}</span>{e(plain(o))}</div>' for i, o in enumerate(options))
    wait = f"{plural(fig['value'], 'day')} open" if fig else "no opened date, so no age"
    rows += f'<div><span class="dc-k">Waiting on</span><span><span class="who">{e(r["owner"] or "nobody named")}</span> <span class="t3">· {e(wait)}</span></span></div>'
    if r["deadline"]:
        rows += f'<div class="dl"><span class="dc-k">Decide by</span>{e(r["deadline"])}</div>'
    return f'<p class="ask">{e(r["id"])}. {e(plain(r["ask"]))}</p><p class="rec">{e(plain(r["recommendation"]))}</p><div class="dc">{rows}</div>'


def call_card(key: dict[str, Any], d: dict[str, Any]) -> str:
    slow = any(i == d["id"] for i, _ in slow_calls(key))
    flag = '<span class="flag">Longer than usual</span>' if slow else ""
    rows = [
        ("Chosen", e(plain(d["chosen"] or "as written"))),
        ("Decided by", f'<span class="who">{e(d["decided_by"])}</span> on {e(d["date"])}{e(took(key, d))}{flag}'),
        ("Owner", f"{e(d['owner'] or 'not named')}, review by {e(d['review_by'] or 'not set')}"),
        ("Can be undone", e(d["reversible"] or "unknown")),
        ("Success signal", e(plain(d["success_signal"] or "none recorded"))),
    ]
    if d.get("assumptions"):
        rows.append(("Assumes", "<ul>" + "".join(f"<li>{e(plain(x))}</li>" for x in d["assumptions"]) + "</ul>"))
    body = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows)
    words = f'<details><summary>In their words</summary><p class="quote">"{e(d["evidence"])}"<span>{e(d["source"])}, checked word for word</span></p></details>'
    return f'<article class="call"><h3><span class="rk">{e(d["id"])}</span>{e(plain(d["title"]))}</h3><dl class="figs">{body}</dl>{words}</article>'


def read_rows(key: dict[str, Any], record: dict[str, Any]) -> str:
    b = key["brief"]
    tested = ", ".join(b["tested_by"]) or "no decision yet"
    rows = [
        ("Target", f"{e(b['metric'])}: {e(b['bar'])} or {e(b['better'])} by {e(b['by'])}"),
        ("Tested by", f"{e(tested)}, the decision whose success signal is the landing brief's target"),
        ("Decides next", f'<span class="who">{e(b["decides"])}</span>, as the landing brief names'),
    ]
    p = record.get("portfolio")
    if isinstance(p, dict):
        parts = [e(x) for x in portfolio_parts(p)]
        text = "; ".join(parts)
        rows.append(("Portfolio", f"{text[:1].upper() + text[1:]}, from the portfolio review of {e(p.get('as_of'))}"))
    else:
        rows.append(("Portfolio", "Not read yet: run the portfolio review first."))
    rows += [("Gap", e(plain(g))) for g in key["gaps"]]
    return '<dl class="figs">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>"


def ledger(key: dict[str, Any]) -> str:
    head = "<tr><th>Figure</th><th class=num>Value</th><th>Window</th></tr>"
    body = "".join(
        f'<tr><td>{e(figure_name(name))}</td><td class="num">{e(figure_text(f))}</td><td class="mono" style="white-space:nowrap">{e(f["window"]["from"])} to {e(f["window"]["to"])}</td></tr>'
        for name, f in key["figures"].items()
    )
    n = len(key["figures"])
    return f'<details><summary>Evidence ledger ({plural(n, "figure")})</summary><div class="tablewrap"><table>{head}{body}</table></div><p class="note">Each figure is counted in code from the decision log; its source is in the engineers\' fold.</p></details>'


def engineers(key: dict[str, Any], record: dict[str, Any]) -> str:
    """Key names, sources, the log's hash and the model ids: none of it is needed to act on the page."""
    head = "<tr><th>Key name</th><th>Source</th></tr>"
    body = "".join(f'<tr><td class="mono">{e(n)}</td><td>{e(f["source"])}</td></tr>' for n, f in key["figures"].items())
    p = record.get("portfolio")
    note = (
        f'<p class="note">Skill: <code>{e(key["tool"].rsplit(" ", 1)[0])}</code> {e(key["tool"].rsplit(" ", 1)[-1])}. Written with <code>--loop</code> and <code>--bet</code>: the <code>decisions</code> key of '
        f"<code>landing/{e(record.get('bet', '<slug>'))}.json</code>, and no other key. Log: <code>{e(key['log']['path'])}</code>, sha256 "
        f"<code>{e(key['log']['sha256'][:12])}</code>. Open decisions are the Leader Report's decision rows ({e(', '.join(key['columns']))}). "
        f"Portfolio read from {e(p.get('tool', 'bet-portfolio-review') if isinstance(p, dict) else 'nothing')}. "
        "Model ids as written: vendor-a/m is the mid-size model, vendor-a/xl the large model.</p>"
    )
    return f'<details><summary>For your engineers</summary><div class="tablewrap eng"><table>{head}{body}</table></div>{note}</details>'


def page(key: dict[str, Any], record: dict[str, Any], title: str) -> str:
    version = "v" + key["tool"].rsplit(" ", 1)[-1]
    header = sk.page_header(NAME, date=f"Read {key['as_of']}", version=version, illustrative=bool(key.get("illustrative")))
    b = key["brief"]
    lede_html = (
        f"{e(title)}: every call on this project names the one person who made it, or the one person it waits on, in their own words. "
        f"The project is tested against its <b>landing brief</b>, a one-page plan: what good looks like, by when, at what cost. "
        f"Here the target is {e(b['metric'].lower())} at {e(b['bar'])} or {e(b['better'])} by {e(b['by'])}."
    )
    pic = days_rows(key) if spans(key) else ""
    cover = (
        f'<section class="slide cover">{header}<h1>{e(verdict(key))}</h1><p class="lede">{lede_html}</p>'
        f'{pic}<div class="cols">{next_box(key)}{glance(key)}</div></section>'
    )
    opens = ""
    if key["rows"]:
        blocks = "".join(open_block(r, key["figures"].get(f"days_waiting@{r['id']}")) for r in key["rows"])
        opens = f'<section class="slide"><div class="meta"><span>Open</span></div><h2>Waiting on a named person</h2>{blocks}</section>'
    calls = "".join(call_card(key, d) for d in key["decided"])
    decided = f'<section class="slide"><div class="meta"><span>Decided</span></div><h2>Who made each call</h2><div class="calls">{calls}</div></section>' if calls else ""
    read = f'<section class="slide"><div class="meta"><span>Read</span></div><h2>What this read</h2>{read_rows(key, record)}</section>'
    detail = f'<section class="slide"><div class="meta"><span>Detail</span></div>{ledger(key)}{engineers(key, record)}</section>'
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(title)}</title><style>{floor_fonts(stylesheet() + sk.CSS + sk.SCORECARD_CSS + PAGE_CSS)}</style></head><body><main class="solo">'
        f"{cover}{opens}{decided}{read}{detail}"
        '<p class="foot">Every figure is counted in code from the decision log, and every decider\'s words are checked against the source word for word. '
        "A decision is open or decided. Whether the project met its target is did-it-land's call, later in the loop.</p></main></body></html>\n"
    )


def markdown(key: dict[str, Any], record: dict[str, Any], title: str) -> str:
    """The plain-text twin of the page."""
    out = [f"# {title}", "", f"Read {key['as_of']} · {NAME} {key['tool'].rsplit(' ', 1)[-1]}" + (" · Illustrative" if key.get("illustrative") else ""), ""]
    out += [f"**{verdict(key)}**", "", lede(key), ""]
    step, who, role, when = next_step(key)
    out += ["## What to do next", "", f"{step} {role}: {who}. When: {when}.", ""]
    rows = spans(key)
    if rows:
        u = usual(key)
        plan = f" · PLAN {u:g} DAYS" if u is not None else ""
        out += ["## Days to decide", "", f"| Decision | Days{plan} | Decided by or waiting on |", "|---|---|---|"]
        for r in rows:
            over = f", {r['days'] - u:g} over plan" if u is not None and r["days"] > u else ""
            days = f"**{plural(r['days'], 'day').upper()}{' WAITING' if r['open'] else ''}**{over}"
            out.append(f"| {r['title']} | {days} | {'open, waiting on ' if r['open'] else ''}{r['who']} |")
        out.append("")
    if key["rows"]:
        out += [
            "## Open, waiting on a named person",
            "",
            "| Id | Decision needed | Options | Recommendation | Decide by | Waiting on | Days waiting |",
            "|---|---|---|---|---|---|---|",
        ]
        out += [
            "| "
            + " | ".join(
                str(x if x is not None else "").replace("|", "\\|")
                for x in (r["id"], plain(r["ask"]), plain(r["options"] or ""), plain(r["recommendation"] or ""), r["deadline"], r["owner"], r["days_waiting"])
            )
            + " |"
            for r in key["rows"]
        ]
        out.append("")
    out += ["## Who made each call", ""]
    for d in key["decided"]:
        out.append(
            f"- {d['id']} {plain(d['title'])}. Chosen: {plain(d['chosen'])}. {d['decided_by']} decided on {d['date']}{took(key, d)}. Owner {d['owner']}, review by {d['review_by']}."
        )
        out.append(f"  Can be undone: {d['reversible'] or 'unknown'}. Success signal: {plain(d['success_signal'] or 'none recorded')}")
        out += [f"  Assumes: {plain(x)}" for x in d.get("assumptions") or []]
    b = key["brief"]
    out += ["", "## What this read", "", f"- Target: {b['metric']}, {b['bar']} or {b['better']} by {b['by']}. Tested by {', '.join(b['tested_by']) or 'no decision yet'}."]
    p = record.get("portfolio")
    if isinstance(p, dict):
        parts = portfolio_parts(p)
        out.append(f"- Portfolio review of {p.get('as_of')}: " + "; ".join(parts) + ".")
    else:
        out.append("- Portfolio: not read yet. Run the portfolio review first.")
    out += [f"- Gap: {plain(g)}" for g in key["gaps"]]
    out += ["", "## Evidence", "", "| Figure | Value | Window |", "|---|---|---|"]
    out += [f"| {figure_name(n)} | {figure_text(f)} | {f['window']['from']} to {f['window']['to']} |" for n, f in key["figures"].items()]
    out += ["", "## For your engineers", "", f"Skill: {key['tool']}.", "", "Each decider's words, checked word for word against the source:", ""]
    out += [f'- {d["id"]}: "{d["evidence"]}" ({d["source"]})' for d in key["decided"]]
    out += ["", "| Key name | Source |", "|---|---|"]
    out += [f"| {n} | {f['source']} |" for n, f in key["figures"].items()]
    out += ["", f"Log: {key['log']['path']}, sha256 {key['log']['sha256'][:12]}. Model ids as written: vendor-a/m is the mid-size model, vendor-a/xl the large model."]
    return "\n".join(out) + "\n"
