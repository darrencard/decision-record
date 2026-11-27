"""The `decisions` key as one self-contained HTML page in the Leader Report style guide, and its Markdown twin.

The page takes the report's whole stylesheet from its template (assets/vendor/template.html, vendored
byte-identical at a pinned commit), so it is the same brand family as the deck. It follows the report's
references/design.md: mono capitals for labels, sans for sentences; hairlines, not boxes; brass for a
person's call (who decides, who it waits on, the deadline). There is no status colour on this page: a
decision is open or decided, and the bet's status words belong to did-it-land. Open decisions are drawn
the way the report's decision slide draws them: options as rows, the deadline in brass.

Nothing is loaded from the network, nothing depends on the clock or the machine, and every piece of
text from a source is escaped.

Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "vendor" / "template.html"
STYLE = re.compile(r"<style>(.*?)</style>", re.S)

# Layout for this page only. Everything else comes from the template's stylesheet.
PAGE_CSS = """
main.solo{margin-left:0}
.solo .slide{min-height:0}
.solo .slide.cover{padding-top:72px;padding-bottom:40px}
.rows{margin-top:8px}
.rows>div{display:grid;grid-template-columns:168px minmax(0,1fr);gap:6px 36px;border-top:1px solid var(--line);padding:14px 0}
.rows>div>span:first-child{font:400 10px/22px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.rows>div>span:last-child{color:var(--t2);font-size:13.5px}
.who{color:var(--brass);font-family:var(--mono);font-size:12.5px}
.ask{font:600 21px/1.25 var(--display);letter-spacing:-.02em;color:var(--t1);margin:28px 0 6px}
.ask:first-of-type{margin-top:0}
.rec{color:var(--t2);font-size:13.5px;margin:0}
.ev{color:var(--t3);font-size:12.5px}
.solo .need{margin-top:24px}
.solo .need-r{margin-top:6px}
.foot{max-width:1120px;margin:0 auto;padding:28px 40px 64px;color:var(--t3);font-size:12px}
@media (max-width:980px){.rows>div{grid-template-columns:1fr;gap:2px}.foot{padding:24px 16px 48px}.solo .slide.cover{padding-top:48px}}
"""

MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">'
    '<rect x="2" y="13" width="3" height="7" fill="var(--agent)"/><rect x="7" y="10" width="3" height="10" fill="var(--agent)"/>'
    '<rect x="12" y="2" width="1.5" height="20" fill="var(--brass)"/><rect x="16" y="4" width="4" height="16" fill="var(--t1)"/></svg>'
)


def e(text: Any) -> str:
    return html.escape(str(text), quote=True)


def stylesheet() -> str:
    """The report template's whole stylesheet, fonts included."""
    try:
        found = STYLE.search(TEMPLATE.read_text(encoding="utf-8"))
    except OSError:
        found = None
    return found.group(1) if found else ""


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def lede(key: dict[str, Any]) -> str:
    """'3 decided, 2 open. 1 past due: D-0004 has waited 14 days on Lead, Quoting squad, against a usual 7.'"""
    f = key["figures"]
    out = f"{f['decided']['value']} decided, {f['open']['value']} open."
    late = [r for r in key["rows"] if f"days_waiting@{r['id']}" in f and "usual_days_to_decide" in f and r["days_waiting"] > f["usual_days_to_decide"]["value"]]
    if late:
        r = late[0]
        who = r["owner"] or "nobody named"
        out += f" {len(late)} past due: {r['id']} has waited {plural(r['days_waiting'], 'day')} on {who}, against a usual {f['usual_days_to_decide']['value']:g}."
    return out


def figure_text(fig: dict[str, Any]) -> str:
    v = fig["value"]
    return f"{v:g} {fig['unit']}" if isinstance(v, float) else f"{v} {fig['unit']}"


def open_block(r: dict[str, Any], fig: dict[str, Any] | None) -> str:
    """One open decision, as the report's decision slide draws it: options as rows, the deadline in brass."""
    options = [o for o in (r["options"] or "").split(" or ") if o]
    rows = "".join(f'<div><span class="dc-k">Option {chr(65 + i)}</span>{e(o)}</div>' for i, o in enumerate(options))
    wait = f"{plural(fig['value'], 'day')} open" if fig else "no opened date, so no age"
    rows += f'<div><span class="dc-k">Waiting on</span><span><span class="who">{e(r["owner"] or "nobody named")}</span> <span class="t3">· {e(wait)}</span></span></div>'
    if r["deadline"]:
        rows += f'<div class="dl"><span class="dc-k">Decide by</span>{e(r["deadline"])}</div>'
    return f'<p class="ask">{e(r["id"])}. {e(r["ask"])}</p><p class="rec">{e(r["recommendation"])}</p><div class="dc">{rows}</div>'


def decided_rows(key: dict[str, Any]) -> str:
    out = []
    for d in key["decided"]:
        fig = key["figures"].get(f"days_to_decide@{d['id']}")
        took = f", {plural(fig['value'], 'day')} after it was opened" if fig else ""
        body = (
            f'<b style="color:var(--t1);font-weight:600">{e(d["title"])}.</b> Chosen: {e(d["chosen"] or "as written")}. '
            f'<span class="who">{e(d["decided_by"])}</span> decided on {e(d["date"])}{e(took)}. '
            f"Owner {e(d['owner'] or 'not named')}, review by {e(d['review_by'] or 'not set')}, reversible {e(d['reversible'] or 'unknown')}.<br>"
            f'<span class="ev">Success signal: {e(d["success_signal"] or "none recorded")}<br>'
            + "".join(f"Assumes: {e(x)}<br>" for x in d.get("assumptions") or [])
            + f'In their words: "{e(d["evidence"])}"</span>'
        )
        out.append(f"<div><span>{e(d['id'])}</span><span>{body}</span></div>")
    return "".join(out)


def loop_rows(key: dict[str, Any], record: dict[str, Any]) -> str:
    b = key["brief"]
    tested = ", ".join(b["tested_by"]) or "no decided record"
    rows = [
        ("Brief", f"{b['metric']}: {b['bar']}, {b['better']} is better, by {b['by']}. Tested by {tested}. The brief says {b['decides']} decides the next step."),
    ]
    p = record.get("portfolio")
    if isinstance(p, dict):
        parts = []
        for name in ("rank", "brief_score"):
            f = p.get(name)
            if isinstance(f, dict) and "value" in f:
                parts.append(f"{name.replace('_', ' ')} {f['value']} ({f['unit']}; {f['source']}, as of {f['as_of']})")
        rows.append(("Portfolio", f"{p.get('tool', 'bet-portfolio-review')}: " + "; ".join(parts) + "."))
    else:
        rows.append(("Portfolio", "Not read: run bet-portfolio-review first."))
    rows.append(("Log", f"{key['log']['path']}, sha256 {key['log']['sha256'][:12]}."))
    rows += [("Gap", g) for g in key["gaps"]]
    return "".join(f"<div><span>{e(k)}</span><span>{e(v)}</span></div>" for k, v in rows)


def ledger(key: dict[str, Any]) -> str:
    head = "<tr><th>Figure</th><th class=num>Value</th><th>Window</th><th>Source</th></tr>"
    body = "".join(
        f'<tr><td class="mono">{e(name)}</td><td class="num">{e(figure_text(f))}</td>'
        f'<td class="mono" style="white-space:nowrap">{e(f["window"]["from"])} to {e(f["window"]["to"])}</td><td>{e(f["source"])}</td></tr>'
        for name, f in key["figures"].items()
    )
    n = len(key["figures"])
    return (
        f'<details><summary>{n} figures, each with its value, window and source</summary><div class="tablewrap" style="margin-top:12px"><table>{head}{body}</table></div></details>'
    )


def page(key: dict[str, Any], record: dict[str, Any], title: str) -> str:
    meta = f"<span>Read {e(key['as_of'])}</span><span>{e(key['tool'])}</span>"
    if key.get("illustrative"):
        meta += '<span class="ill">Illustrative</span>'
    opens = "".join(open_block(r, key["figures"].get(f"days_waiting@{r['id']}")) for r in key["rows"]) or '<p class="rec">No open decisions.</p>'
    who = key.get("next_step_by")
    call = (
        f'<div class="need"><b>Next step</b><div class="need-r"><p>{e(key["next_step"])}</p>'
        + (f'<span class="mono" style="color:var(--brass);font-size:11px">{e(who)}</span>' if who else "")
        + f'</div><p style="margin-top:8px">{e(key["next_in_loop"])}</p></div>'
    )
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(title)}</title><style>{stylesheet()}{PAGE_CSS}</style></head><body><main class="solo">'
        f'<section class="slide cover"><div class="brand">{MARK}<span translate="no">DACARD</span></div><div class="meta">{meta}</div>'
        f'<h1>{e(title)}</h1><p class="lede">{e(lede(key))} Every call names the one person who made it, or the one person it waits on.</p>{call}</section>'
        f'<section class="slide"><div class="meta"><span>Open</span><span>As the Leader Report shows them</span></div><h2>Waiting on a named person</h2>{opens}</section>'
        f'<section class="slide"><div class="meta"><span>Decided</span></div><h2>Who made each call</h2><div class="rows">{decided_rows(key)}</div></section>'
        f'<section class="slide"><div class="meta"><span>Loop</span><span>01 Decide</span></div><h2>What it read</h2><div class="rows">{loop_rows(key, record)}</div></section>'
        f'<section class="slide"><div class="meta"><span>Ledger</span></div><h2>Every figure, with its source</h2>{ledger(key)}</section>'
        '<p class="foot">Every figure is counted in code from the decision log, and every decider\'s words are checked against the source word for word. '
        "A decision is open or decided. Whether the bet met its bar is did-it-land's call, later in the loop.</p></main></body></html>\n"
    )


def markdown(key: dict[str, Any], record: dict[str, Any], title: str) -> str:
    """The plain-text twin of the page."""
    out = [f"# {title}", "", f"Read {key['as_of']} · {key['tool']}" + (" · Illustrative" if key.get("illustrative") else ""), ""]
    out += [lede(key), "", f"Next step: {key['next_step']}", "", key["next_in_loop"], "", "## Open, as the Leader Report shows them", ""]
    cols = key["columns"]
    out += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if r[c] is None else str(r[c]).replace("|", "\\|") for c in cols) + " |" for r in key["rows"]]
    out += ["", "## Decided", ""]
    for d in key["decided"]:
        out.append(f"- {d['id']} {d['title']}. Chosen: {d['chosen']}. {d['decided_by']} decided on {d['date']}. Owner {d['owner']}, review by {d['review_by']}.")
        out.append(f"  Reversible: {d['reversible'] or 'unknown'}. Success signal: {d['success_signal'] or 'none recorded'}")
        out += [f"  Assumes: {x}" for x in d.get("assumptions") or []]
        out.append(f'  In their words: "{d["evidence"]}"')
    b = key["brief"]
    out += ["", "## What it read", "", f"- Brief: {b['metric']}, {b['bar']}, {b['better']} is better, by {b['by']}. Tested by {', '.join(b['tested_by']) or 'no decided record'}."]
    p = record.get("portfolio")
    if isinstance(p, dict):
        parts = [f"{n.replace('_', ' ')} {p[n]['value']} ({p[n]['unit']})" for n in ("rank", "brief_score") if isinstance(p.get(n), dict) and "value" in p[n]]
        out.append(f"- Portfolio: {p.get('tool', 'bet-portfolio-review')}, as of {p.get('as_of')}: " + "; ".join(parts) + ".")
    else:
        out.append("- Portfolio: not read. Run bet-portfolio-review first.")
    out += [f"- Gap: {g}" for g in key["gaps"]]
    out += ["", "## Ledger", "", "| Figure | Value | Window | Source |", "|---|---|---|---|"]
    out += [f"| {n} | {figure_text(f)} | {f['window']['from']} to {f['window']['to']} | {f['source']} |" for n, f in key["figures"].items()]
    return "\n".join(out) + "\n"
