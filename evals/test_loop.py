"""Hold decision-record's Landing Loop step (01 Decide) to its promises.

Run: python3 -m unittest discover -s evals -v   (or python3 -m pytest evals)

Groups:
  Vendored     the brief parser and template are byte for byte what VENDORED.json pins.
  Sample       the README's Acme command reproduces the committed files byte for byte.
  LoopRecord   only the `decisions` key is written; every key it reads, and every later key, is kept as found.
  Figures      every figure carries value, unit, source, window (from, to) and as_of.
  StatusWords  landed, watch and stalled never appear in what this skill writes.
  LeaderReport the key's rows are the report's decision format, unchanged.
  Refusals     a changed or incomplete brief, or an invalid log, writes nothing.
  Page         one self-contained page; brass only for a person's call.
  FromThread   Slack, Linear and CSV exports become a source the checks read.

Acme is an invented company. Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "decision-record"
SCRIPTS = SKILL / "scripts"
ACME = ROOT / "examples" / "acme"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "vendor"))

import declog  # noqa: E402
import from_thread  # noqa: E402
import landing_brief  # noqa: E402
import loop  # noqa: E402
import open_decisions  # noqa: E402
import render_html  # noqa: E402
import svgkit  # noqa: E402

BET = "quote-drafting"
AS_OF = "2026-11-26"  # the record key: the full log, read late in the loop
DECIDE_STEP = "2026-07-27"  # the Decide-step view, read with no record write
STATUS_WORDS = re.compile(r"\b(landed|watch|stalled)\b", re.I)
SAMPLE_OUTPUTS = (
    "decisions.md", "decision-record.html", "decision-record.md", "leader-report-decisions.md", f"landing/{BET}.json",
    "decide-step/decisions.md", "decide-step/open-decisions.md",
)  # fmt: skip


def landing_brief_for_acme():
    return loop.read_brief(ACME / "briefs" / f"{BET}.md")


def figures_in(obj, prefix=""):
    if isinstance(obj, dict):
        if "value" in obj and "source" in obj:
            return [(prefix, obj)]
        return [x for k, v in obj.items() for x in figures_in(v, f"{prefix}.{k}" if prefix else k)]
    if isinstance(obj, list):
        return [x for i, v in enumerate(obj) for x in figures_in(v, f"{prefix}[{i}]")]
    return []


class Work(unittest.TestCase):
    """A working folder holding the Acme briefs, the upstream record and the Acme log."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        shutil.copytree(ACME / "briefs", self.dir / "briefs")
        (self.dir / "landing").mkdir()
        self.record = self.dir / "landing" / f"{BET}.json"
        shutil.copy(ACME / "upstream" / "bet-portfolio-review.json", self.record)
        self.log = self.dir / "decisions.md"
        shutil.copy(ACME / "decisions.md", self.log)

    def tearDown(self):
        self._tmp.cleanup()

    def run_loop(self, *extra):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = open_decisions.main(["--log", str(self.log), "--as-of", AS_OF, "--loop", str(self.dir), "--bet", BET, *extra])
        return code, err.getvalue()


class Vendored(unittest.TestCase):
    def test_every_vendored_file_matches_its_pin(self):
        pins = json.loads((SKILL / "VENDORED.json").read_text(encoding="utf-8"))
        self.assertRegex(pins["commit"], r"^[0-9a-f]{40}$")
        for rel, pin in pins["files"].items():
            with self.subTest(rel=rel):
                self.assertEqual(hashlib.sha256((SKILL / rel).read_bytes()).hexdigest(), pin["sha256"], f"{rel} changed. Copy it again and update VENDORED.json.")
        self.assertTrue(pins["files"]["scripts/landing_brief.py"]["sha256"].startswith("2d13573543c74ebe"))

    def test_the_acme_brief_parses_with_the_vendored_parser(self):
        b = landing_brief.parse((ACME / "briefs" / f"{BET}.md").read_text(encoding="utf-8"))
        self.assertEqual((b.metric, b.bar_text, b.by), ("Quote draft acceptance rate", "40%", "2026-11-15"))

    def test_upstream_is_the_landing_loop_record_filtered_to_what_this_skill_reads(self):
        up = json.loads((ACME / "upstream" / "bet-portfolio-review.json").read_text(encoding="utf-8"))
        self.assertEqual(list(up), ["schema", "bet", "brief", "portfolio"])
        self.assertEqual(up["brief"]["sha256"], hashlib.sha256((ACME / "briefs" / f"{BET}.md").read_bytes()).hexdigest())


class Sample(unittest.TestCase):
    def test_the_readme_command_reproduces_the_committed_files(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("python3 examples/acme/sample.py", readme)
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(ACME / "sample.py"), "--into", tmp], capture_output=True, text=True, timeout=60, cwd=ROOT)  # noqa: S603
            self.assertEqual(done.returncode, 0, done.stderr)
            for name in SAMPLE_OUTPUTS:
                with self.subTest(name=name):
                    self.assertEqual((Path(tmp) / name).read_bytes(), (ACME / name).read_bytes(), f"{name} differs. Run python3 examples/acme/sample.py and commit.")


class Story(unittest.TestCase):
    """The record key and the Decide-step view tell one story with the rest of the loop."""

    def test_the_key_reads_the_full_log_and_only_brief_and_portfolio(self):
        rec = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))
        key = rec["decisions"]
        self.assertEqual(key["as_of"], AS_OF)
        self.assertEqual(key["reads"], {"brief": True, "portfolio": True})
        self.assertEqual(list(rec), ["schema", "bet", "brief", "portfolio", "decisions"])
        by = {d["id"]: d for d in key["decided"]}
        trigger, tier = by["D-0004"], by["D-0005"]
        self.assertEqual((trigger["decided_by"], trigger["owner"]), ("Head of Product, Quoting squad", "Tech lead, Quoting squad"))
        self.assertEqual(trigger["chosen"], "Roll back when wrong-price quotes pass 2%")
        self.assertTrue("2026-08-03" < trigger["date"] < "2026-09-05")  # after the spec hold, before the release read
        self.assertLess(tier["date"], "2026-11-15")  # before the cost read
        self.assertEqual(tier["chosen"], "vendor-a/m")
        for d in (trigger, tier):
            self.assertEqual(d["source"], "Acme spec review call, 2026-08-10 (illustrative)")

    def test_the_page_keeps_the_decide_step_history(self):
        md = (ACME / "decision-record.md").read_text(encoding="utf-8")
        self.assertIn("5 decided, 0 open. 2 took longer than the usual 14 days to decide: D-0004 (28 days), D-0005 (21 days).", md)
        self.assertIn("decided on 2026-08-10, 28 days after it was opened, longer than the usual 14.", md)
        self.assertNotIn("past due", md)

    def test_the_decide_step_view_shows_both_calls_open(self):
        step = declog.parse_log((ACME / "decide-step" / "decisions.md").read_text(encoding="utf-8"))
        self.assertEqual([r.id for r in step if r.status == "open"], ["D-0004", "D-0005"])
        self.assertEqual(declog.validate_log(step, date.fromisoformat(DECIDE_STEP)), [])
        view = (ACME / "decide-step" / "open-decisions.md").read_text(encoding="utf-8")
        self.assertIn("2 open · oldest 14 days · 1 waiting longer than usual", view)
        self.assertIn("| D-0004 | Set the rollback trigger for quote drafting | 14 | Lead, Quoting squad | longer than usual |", view)
        self.assertNotIn("past due", view)  # D-0004's deadline, 2026-08-03, is still ahead on 2026-07-27

    def test_the_readme_shows_the_decide_step_view(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("--log examples/acme/decide-step/decisions.md --as-of 2026-07-27", readme)

    def test_past_due_means_a_passed_deadline_not_a_long_wait(self):
        records = declog.parse_log((ACME / "decide-step" / "decisions.md").read_text(encoding="utf-8"))
        key = loop.build(records, date(2026, 8, 4), {"path": "decisions.md", "sha256": "0" * 64}, landing_brief_for_acme(), None)
        self.assertEqual(key["figures"]["past_due"]["value"], 2)
        self.assertIn("2 past due: D-0004 was to be decided by 2026-08-03.", render_html.lede(key))
        early = loop.build(records, date.fromisoformat(DECIDE_STEP), {"path": "decisions.md", "sha256": "0" * 64}, landing_brief_for_acme(), None)
        self.assertEqual(
            render_html.lede(early),
            "3 decided, 2 open. 1 waiting longer than usual: D-0004 has waited 14 days on Lead, Quoting squad, against a usual 7. "
            "1 took longer than the usual 7 days to decide: D-0002 (14 days).",
        )


class EntryScripts(unittest.TestCase):
    def test_every_entry_script_checks_python_before_anything_else(self):
        vendored = set(json.loads((SKILL / "VENDORED.json").read_text(encoding="utf-8"))["files"])
        for path in sorted(SCRIPTS.glob("*.py")):
            if f"scripts/{path.name}" in vendored or '__name__ == "__main__"' not in (text := path.read_text(encoding="utf-8")):
                continue
            with self.subTest(script=path.name):
                check = text.find("sys.version_info < (3, 11)")
                self.assertGreater(check, 0)
                self.assertIn("try python3.12", text)
                for io_call in ("read_text(", "write_text(", "open("):
                    first = text.find(io_call, text.find('"""', 3) + 3)
                    self.assertTrue(first == -1 or first > check, f"{path.name}: {io_call} before the version check")

    def test_decide_rewrites_the_log_through_a_temp_file(self):
        import record

        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "decisions.md"
            shutil.copy(ACME / "decide-step" / "decisions.md", log)
            args = ["decide", "D-0005", "--decided-by", "Tech lead, Quoting squad", "--date", "2026-08-10", "--evidence", "x", "--source-name", "Spec review"]
            with contextlib.redirect_stdout(io.StringIO()):
                code = record.main([*args, "--as-of", "2026-11-26", "--log", str(log)])
            self.assertEqual(code, 0)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["decisions.md"])
            self.assertEqual(next(r for r in declog.parse_log(log.read_text(encoding="utf-8")) if r.id == "D-0005").source, "Spec review")


class LoopRecord(Work):
    def test_writes_only_its_own_key_and_keeps_read_keys_byte_identical(self):
        before = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(self.run_loop()[0], 0)
        after = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(set(after) - set(before), {"decisions"})
        for k in before:
            self.assertEqual(json.dumps(after[k], indent=2, ensure_ascii=False), json.dumps(before[k], indent=2, ensure_ascii=False), k)
        # The block each read key had in the file is in the new file verbatim.
        text = self.record.read_text(encoding="utf-8")
        block = json.dumps({"portfolio": before["portfolio"]}, indent=2, ensure_ascii=False)[2:-2]
        self.assertIn(block, text)

    def test_the_committed_record_holds_the_upstream_keys_unchanged(self):
        up = json.loads((ACME / "upstream" / "bet-portfolio-review.json").read_text(encoding="utf-8"))
        rec = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))
        self.assertEqual(list(rec), ["schema", "bet", "brief", "portfolio", "decisions"])
        for k in up:
            self.assertEqual(rec[k], up[k], k)

    def test_later_keys_are_kept_and_never_read(self):
        rec = json.loads(self.record.read_text(encoding="utf-8"))
        rec["landed"] = {"status": "stalled", "note": "a later step"}
        rec["spec"] = {"verdict": "hold"}
        self.record.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(self.run_loop()[0], 0)
        after = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual((after["landed"], after["spec"]), (rec["landed"], rec["spec"]))
        self.assertEqual(list(after), ["schema", "bet", "brief", "portfolio", "decisions", "spec", "landed"])
        self.assertNotIn("stalled", json.dumps(after["decisions"]))

    def test_rerun_gives_the_same_bytes(self):
        self.run_loop()
        first = self.record.read_bytes()
        self.run_loop()
        self.assertEqual(self.record.read_bytes(), first)

    def test_no_portfolio_is_a_gap_not_a_guess(self):
        rec = json.loads(self.record.read_text(encoding="utf-8"))
        del rec["portfolio"]
        self.record.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(self.run_loop()[0], 0)
        key = json.loads(self.record.read_text(encoding="utf-8"))["decisions"]
        self.assertFalse(key["reads"]["portfolio"])
        self.assertIn("portfolio not read: run bet-portfolio-review first", key["gaps"])

    def test_a_new_record_starts_from_the_brief(self):
        self.record.unlink()
        self.assertEqual(self.run_loop("--brief", str(self.dir / "briefs" / f"{BET}.md"))[0], 0)
        rec = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(rec["brief"]["path"], f"briefs/{BET}.md")
        self.assertEqual(list(rec), ["schema", "bet", "brief", "decisions"])

    def test_named_people_own_every_decision(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        for r in key["rows"]:
            self.assertTrue(declog.is_named_decider(r["owner"]), r)
        for d in key["decided"]:
            self.assertTrue(declog.is_named_decider(d["decided_by"]), d)
            self.assertTrue(declog.is_scoped_role(d["decided_by"]), d)
        self.assertEqual(key["brief"]["tested_by"], ["D-0001"])
        self.assertEqual(key["decided"][0]["decided_by"], key["brief"]["decides"])  # the brief's own scoped role
        self.assertIsNone(key["next_step_by"])  # nothing is open on 2026-11-26
        self.assertEqual(key["next_step"], "No open decisions on this project.")
        self.assertEqual(key["next_in_loop"], "")  # no hand-on line while nothing is open
        self.assertEqual(key["rows"], [])


class Figures(unittest.TestCase):
    def test_every_figure_carries_source_and_window(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        figs = figures_in(key)
        self.assertGreaterEqual(len(figs), 8)
        self.assertEqual({n for n, _ in figs}, {f"figures.{k}" for k in key["figures"]})
        for name, f in figs:
            with self.subTest(name=name):
                self.assertEqual(set(f), {"value", "unit", "source", "window", "as_of"})
                self.assertTrue(f["source"] and f["unit"])
                self.assertEqual(set(f["window"]), {"from", "to"})
                for d in (f["window"]["from"], f["window"]["to"], f["as_of"]):
                    date.fromisoformat(d)
                self.assertLessEqual(f["window"]["from"], f["window"]["to"])

    def test_acme_figures_match_the_log(self):
        f = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]["figures"]
        got = {k: f[k]["value"] for k in ("open", "decided", "waiting_long", "past_due", "usual_days_to_decide", "days_to_decide@D-0004", "days_to_decide@D-0005")}
        self.assertEqual(got, {"open": 0, "decided": 5, "waiting_long": 0, "past_due": 0, "usual_days_to_decide": 14.0, "days_to_decide@D-0004": 28, "days_to_decide@D-0005": 21})
        self.assertNotIn("oldest_open", f)


class StatusWords(unittest.TestCase):
    def test_no_bet_status_word_in_what_this_skill_writes(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        texts = {
            "key": json.dumps(key),
            "html": re.sub(r"<style>.*?</style>", "", (ACME / "decision-record.html").read_text(encoding="utf-8"), flags=re.S),
            "md": (ACME / "decision-record.md").read_text(encoding="utf-8"),
            "log": (ACME / "decisions.md").read_text(encoding="utf-8"),
            "export": (ACME / "leader-report-decisions.md").read_text(encoding="utf-8"),
        }
        for name, text in texts.items():
            with self.subTest(name=name):
                self.assertIsNone(STATUS_WORDS.search(text), name)

    def test_outcomes_use_their_own_words_and_read_old_logs(self):
        self.assertEqual(declog.OUTCOMES, ("worked", "pending", "missed"))
        old = "## D-0001: X\n\n- Status: decided\n- Outcome: landed\n"
        self.assertEqual(declog.parse_log(old)[0].outcome, "worked")


class LeaderReport(unittest.TestCase):
    def test_rows_are_the_reports_decision_format(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        self.assertEqual(key["columns"][:4], ["ask", "options", "recommendation", "deadline"])
        records = declog.parse_log((ACME / "decisions.md").read_text(encoding="utf-8"))
        rows, problems = declog.leader_report_rows(records, date.fromisoformat(AS_OF))
        self.assertEqual((key["rows"], problems), (rows, []))
        step = declog.parse_log((ACME / "decide-step" / "decisions.md").read_text(encoding="utf-8"))
        step_rows, problems = declog.leader_report_rows(step, date.fromisoformat(DECIDE_STEP))
        self.assertEqual(([r["id"] for r in step_rows], problems), (["D-0004", "D-0005"], []))
        for r in step_rows:
            self.assertEqual(list(r), list(declog.LEADER_REPORT_COLUMNS + declog.LEADER_REPORT_EXTRA))
            self.assertNotIn(" or ", r["options"].replace(" or ", "|", 1))

    def test_rows_match_the_markdown_export(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        lines = [ln for ln in (ACME / "leader-report-decisions.md").read_text(encoding="utf-8").splitlines() if ln.startswith("| ") and "---" not in ln]
        head = [c.strip() for c in lines[0].strip("|").split("|")]
        body = [dict(zip(head, (c.strip() for c in ln.strip("|").split("|")), strict=True)) for ln in lines[1:]]
        self.assertEqual([b["ask"] for b in body], [r["ask"] for r in key["rows"]])
        self.assertEqual([b["deadline"] for b in body], [r["deadline"] for r in key["rows"]])


class Refusals(Work):
    def test_a_brief_changed_after_the_record_opened_writes_nothing(self):
        before = self.record.read_bytes()
        brief = self.dir / "briefs" / f"{BET}.md"
        brief.write_text(brief.read_text(encoding="utf-8").replace("40%", "35%"), encoding="utf-8")
        code, err = self.run_loop()
        self.assertEqual(code, 2)
        self.assertIn("changed after the record was opened", err)
        self.assertEqual(self.record.read_bytes(), before)

    def test_an_incomplete_brief_is_refused_by_the_parsers_own_check(self):
        self.record.unlink()
        brief = self.dir / "briefs" / "thin.md"
        brief.write_text("# Thin\n\n## Landing brief\n\n- **Metric:** Quote draft acceptance rate\n", encoding="utf-8")
        code, err = self.run_loop("--brief", str(brief))
        self.assertEqual(code, 2)
        self.assertIn("the landing brief cannot be used", err)
        self.assertFalse(self.record.exists())

    def test_an_invalid_log_writes_nothing(self):
        before = self.record.read_bytes()
        self.log.write_text(self.log.read_text(encoding="utf-8").replace("- Decided by: Tech lead, Quoting squad", "- Decided by: The team"), encoding="utf-8")
        code, err = self.run_loop()
        self.assertEqual(code, 2)
        self.assertIn("invalid record", err)
        self.assertEqual(self.record.read_bytes(), before)

    def test_a_record_for_another_bet_is_left_alone(self):
        with self.assertRaises(loop.RecordError):
            loop.load(self.record, "payment-links")


class Page(unittest.TestCase):
    def setUp(self):
        self.html = (ACME / "decision-record.html").read_text(encoding="utf-8")
        self.body = re.sub(r"<style>.*?</style>", "", self.html, flags=re.S)

    def test_self_contained(self):
        self.assertNotRegex(self.html, r"""(src|href)=["']?https?://""")
        self.assertNotIn("<script", self.html)
        self.assertNotIn("@import", self.html)

    def test_illustrative_tag_is_visible(self):
        self.assertIn('<span class="sk-ill">Illustrative</span>', self.body)
        self.assertIn(":root{--ill:#74A5DA}", self.html, "the Illustrative tag is blue")

    def test_selection_and_focus_ring_are_ink_not_green(self):
        css = self.html[self.html.index("::selection{background:var(--t1)") :]
        self.assertIn(":focus-visible{outline-color:var(--t1)}", css)
        self.assertNotIn("var(--landed)", css)

    def test_no_status_colour_and_brass_only_for_a_persons_call(self):
        self.assertNotIn('class="st', self.body)
        self.assertNotIn("var(--landed)", self.body)
        self.assertNotIn("var(--stalled)", self.body)
        brass = re.findall(r'<span class="who">([^<]*)</span>', self.body)
        self.assertEqual(set(brass), {"Head of Product, Quoting squad", "Tech lead, Quoting squad"})
        # Brass paints the brand mark's bar in the body; the person marks take it from the stylesheet, one per decision.
        self.assertEqual(self.body.count("var(--brass)"), 1)
        frame = svgkit.frames_in(self.html)[0]
        self.assertEqual(frame.count('<span class="sc-o">'), 5)
        css = self.html.split("<style>", 1)[1].split("</style>", 1)[0]
        for sel in __import__("re").findall(r"([^{}]+)\{[^{}]*var\(--brass\)", svgkit.SCORECARD_CSS):
            self.assertRegex(sel.strip(), r"\.sc-(o|pm)\b")
        self.assertIn(".scg .sc-o{", css)

    def test_the_page_follows_the_sample_anatomy(self):
        body = self.body.split('<main class="solo">', 1)[1]
        order = ['class="sk-hdr"', "<h1>", 'role="img"', "What to do next", 'class="calls"', "Evidence ledger", "For your engineers"]
        at = [body.index(x) for x in order]
        self.assertEqual(at, sorted(at))
        self.assertIn("<h1>All five decisions are made; none is open. Two took longer than usual to decide.</h1>", body)
        self.assertEqual(body.count('<div class="next">'), 1, "one next step leads the page")
        self.assertIn('<span class="o"><i>Decides</i>Head of Product, Quoting squad</span><span class="d"><i>When</i>was due 2026-11-15</span>', body)
        self.assertNotIn("Book a call", body, "a sample is the skill's own output: no call to action")

    def test_a_shared_team_prints_once(self):
        self.assertEqual(render_html.common_scope(["Head of Product, Quoting squad", "Tech lead, Quoting squad"]), "Quoting squad")
        self.assertIsNone(render_html.common_scope(["Head of Product, Quoting squad", "Tech lead, Payments team"]))
        self.assertIsNone(render_html.common_scope(["Head of Product, Quoting squad", "nobody named"]))
        self.assertIsNone(render_html.common_scope([]))

    def test_the_rows_print_each_decision_its_days_and_who_made_it(self):
        self.assertEqual(svgkit.unprinted(self.html), [])
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        frames = svgkit.frames_in(self.html)
        self.assertEqual(len(frames), 1)
        frame = frames[0]
        self.assertEqual(frame.count('<div class="sc-r">'), len(key["decided"]))
        for d in key["decided"]:
            days = key["figures"]["days_to_decide@" + d["id"]]["value"]
            self.assertIn(f'<span class="sc-l"><b>{days} DAYS</b></span>', frame)
            role = d["decided_by"].rsplit(", ", 1)[0]
            self.assertIn(f"</svg>{render_html.e(role)}</span>", frame, "each row prints only the role")
        for f in re.findall(r'<span class="sc-l">(.*?)</span>', frame):
            text = re.sub(r"<[^>]+>", "", f)
            self.assertEqual(text, text.upper(), "the figure column is numerals and uppercase words")
        # The team every role shares prints once, in the frame head, so no role wraps to two lines.
        self.assertEqual(frame.count("Quoting squad"), 1)
        self.assertIn('<span class="sc-k">Quoting squad</span></span><span class="sc-i">', frame)
        # The plan is printed once, in the frame head; the part past it is hatched on exactly the two slow calls.
        self.assertEqual(frame.count("plan 14 days"), 1)
        self.assertEqual(frame.count('class="ov"'), 2)
        self.assertEqual(frame.count('<span class="sc-k"><i class="k-o"></i>over plan</span>'), 1)

    def test_the_scorecard_is_rows_with_no_text_inside_a_picture(self):
        css = self.html.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertEqual(svgkit.svgs_with_text(self.html), [], "text inside an SVG")
        self.assertEqual(svgkit.scaled_svgs_in(self.html), [], "a picture with a viewBox would scale")
        self.assertEqual(set(svgkit.font_sizes(css)), {"var(--sc-m)", "var(--sc-n)"})
        self.assertIn("--sc-m:calc(12px / var(--sc-z))", css)
        self.assertIn("--sc-n:calc(14px / var(--sc-z))", css)
        self.assertEqual(svgkit.boxes_in_frames(self.html, css), [], "a box inside the frame")
        self.assertNotIn("position:absolute", svgkit.SCORECARD_CSS)
        self.assertNotIn('class="chip', self.body, "words print as text, never boxed chips")

    def test_no_legacy_svgkit_primitive_draws_on_the_page(self):
        import warnings

        self.assertEqual(svgkit.legacy_in(self.html), [])
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            render_html.page(key, {}, "T")

    def test_open_calls_show_open_and_who_they_wait_on(self):
        records = declog.parse_log((ACME / "decide-step" / "decisions.md").read_text(encoding="utf-8"))
        key = loop.build(records, date.fromisoformat(DECIDE_STEP), {"path": "decisions.md", "sha256": "0" * 64}, landing_brief_for_acme(), None)
        out = render_html.page(key, {}, "T")
        self.assertEqual(svgkit.unprinted(out), [])
        frame = svgkit.frames_in(out)[0]
        self.assertEqual(frame.count('<span class="sc-w ink">open</span>'), 2)
        self.assertEqual(frame.count('<span class="sc-o">'), 5, "one person per row: who decided, or who it waits on")
        self.assertIn("DAYS WAITING", frame)
        self.assertIn("<h1>Two of five decisions are still open. D-0004 has waited longer than usual on Lead, Quoting squad.</h1>", out)
        self.assertIn("<p>Decide D-0004: set when to undo quote drafting.</p>", out)

    def test_each_visual_states_its_answer(self):
        labels = re.findall(r'role="img" aria-label="([^"]+)"', self.html)
        self.assertEqual(
            labels,
            ["Five decisions from the day each was raised to the day a named person made it; D-0004 took 28 days and D-0005 took 21 days, longer than the usual 14."],
        )

    def test_public_copy_uses_plain_words(self):
        public = re.sub(r"<details>.*?</details>", " ", self.body.split("Evidence ledger", 1)[0], flags=re.S)
        public = svgkit.page_text("</style>" + public).lower()
        for word in (" bet ", " bets ", " bar ", "rollback", "roll back", "vendor-a", "tokens per task", ".json", "_"):
            self.assertNotIn(word, public, word)
        self.assertIn("<b>landing brief</b>, a one-page plan", self.body)
        md = (ACME / "decision-record.md").read_text(encoding="utf-8").split("## For your engineers", 1)[0].lower()
        for word in (" bet ", " bets ", "rollback", "roll back", "vendor-a", "tokens per task"):
            self.assertNotIn(word, md, word)

    def test_no_text_smaller_than_11px(self):
        css = "".join(re.findall(r"<style>(.*?)</style>", self.html, re.S))
        decls = re.findall(r"font(?:-size)?:[^;}]*", css)
        self.assertTrue(decls)
        sizes = [float(n) for d in decls for n in re.findall(r"(?<![/\d.])(\d+(?:\.\d+)?)px", d)]
        self.assertGreaterEqual(min(sizes), 11, "a font size below 11px")
        self.assertNotRegex(self.html, r'font-size="(\d|10)(\.\d+)?"', "an SVG label below 11px")
        template = (SKILL / "assets" / "vendor" / "template.html").read_text(encoding="utf-8")
        self.assertIn("font:400 10px/16px var(--mono)", template, "the template stays as vendored; the page raises its sizes")

    def test_header_prints_the_plain_name_and_the_fold_the_code_name(self):
        header = re.search(r'<header class="sk-hdr">.*?</header>', self.html, re.S).group(0)
        self.assertIn("<span>Decision record</span>", header)
        self.assertNotIn("decision-record", header)
        fold = self.html.split("<summary>For your engineers</summary>", 1)[1]
        self.assertRegex(fold, r"Skill: <code>decision-record</code> \d")
        md = (ACME / "decision-record.md").read_text(encoding="utf-8")
        self.assertRegex(md.splitlines()[2], r"^Read \S+ · Decision record \d")
        self.assertRegex(md.split("## For your engineers", 1)[1], r"Skill: decision-record \d")

    def test_no_internal_words_in_public_copy(self):
        # The page's own name, Decision record, is the one exception.
        banned = re.compile(r"\b(records?|bets?|the bar|PRDs?|ARR|tokens?)\b", re.I)
        public = re.sub(r"<details><summary>For your engineers</summary>.*?</details>", " ", self.html.split("</style>", 1)[1], flags=re.S)
        text = svgkit.page_text(public).replace("DECISION RECORD", "")
        self.assertIsNone(banned.search(text), "internal word on the page")
        self.assertIn("<h2>What this read</h2>", self.html)
        self.assertIn("AI usage of 9,000 per task", self.html)
        md = (ACME / "decision-record.md").read_text(encoding="utf-8").split("## For your engineers", 1)[0].replace("Decision record", "")
        self.assertIsNone(banned.search(md), "internal word in the Markdown twin")

    def test_svgkit_matches_its_landing_loop_pin(self):
        pin = json.loads((SKILL / "VENDORED.json").read_text(encoding="utf-8"))["landing-loop"]
        self.assertEqual(pin["commit"], "78784efd2ecd5282f6ec264e545ce2075e459be2")
        self.assertEqual(set(pin["files"]), {"scripts/vendor/svgkit.py"})
        for rel, info in pin["files"].items():
            digest = hashlib.sha256((SKILL / rel).read_bytes()).hexdigest()
            self.assertEqual(digest, info["sha256"], f"{rel} changed. Copy it again from landing-loop at the pinned commit and update VENDORED.json.")

    def test_source_text_is_escaped(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        key = json.loads(json.dumps(key))
        key["decided"][0]["title"] = "<script>alert(1)</script>"
        out = render_html.page(key, {}, "T")
        self.assertNotIn("<script>alert", out)
        self.assertIn("&lt;script&gt;", out)


class FromThread(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, data):
        p = self.dir / name
        p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return p

    def convert(self, *args):
        out = self.dir / "source.txt"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = from_thread.main([*args, "--out", str(out)])
        return code, out.read_text(encoding="utf-8") if out.exists() else ""

    def test_slack_with_user_ids_becomes_a_checked_source(self):
        hist = self.write(
            "h.json",
            {
                "messages": [
                    {"ts": "1785147300.0001", "user": "U2", "text": "My call: approve before send."},
                    {"ts": "1785146400.0001", "user": "U1", "text": "Options?\nInjected: line"},
                ]
            },
        )
        users = self.write("u.json", {"members": [{"id": "U1", "real_name": "Tom Okafor"}, {"id": "U2", "profile": {"real_name": "Maya Ortiz"}}]})
        code, text = self.convert("--slack", str(hist), "--users", str(users))
        self.assertEqual(code, 0)
        lines = text.splitlines()
        self.assertEqual(lines[1:], ["[2026-07-27 10:00] Tom Okafor: Options? Injected: line", "[2026-07-27 10:15] Maya Ortiz: My call: approve before send."])
        utter = declog.parse_source(text)
        hit = declog.find_quote("My call: approve before send.", utter)
        self.assertEqual((hit["speaker"], hit["date"]), ("Maya Ortiz", "2026-07-27"))
        self.assertNotIn("From", declog.speakers(utter))

    def test_linear_comments(self):
        data = self.write("c.json", {"data": {"comments": {"nodes": [{"body": "Decided: ship it.", "createdAt": "2026-07-27T09:30:00.000Z", "user": {"name": "Priya Raman"}}]}}})
        code, text = self.convert("--linear", str(data))
        self.assertEqual((code, text.splitlines()[1]), (0, "[2026-07-27 09:30] Priya Raman: Decided: ship it."))

    def test_csv_fallback_and_its_refusal(self):
        good = self.write("t.csv", "when,who,text\n2026-07-27 10:00,Tom Okafor,We still need a rollback trigger.\n")
        self.assertEqual(self.convert("--csv", str(good))[1].splitlines()[1], "[2026-07-27 10:00] Tom Okafor: We still need a rollback trigger.")
        bad = self.write("b.csv", "when,who,text\n27/07/2026,Tom Okafor,x\n")
        self.assertEqual(self.convert("--csv", str(bad))[0], 2)

    def test_a_wrong_shape_is_refused(self):
        self.assertEqual(self.convert("--slack", str(self.write("x.json", {"ok": True})))[0], 2)


class FullColumn(unittest.TestCase):
    """Text runs the full content column, as wide as the scorecard frame (2026-11-27): no max-width on h1, .lede or p."""

    def test_page_css_sets_no_max_width_on_text(self) -> None:
        css = render_html.PAGE_CSS
        for selector, body in re.findall(r"([^{}]+)\{([^}]*max-width:[^}]*)\}", css):
            if re.search(r"(^|[\s,])(h1|\.lede|p|li|\.next|\.note|\.figs|\.checks)([\s,:.]|$)", selector):
                self.assertIn("max-width:none", body, selector)
        self.assertIn(".solo h1,.solo .lede,.solo .next,.solo .slide p,.solo .slide li,.solo .sc-c,.sk figcaption{max-width:none}", css)
        self.assertIn("text-wrap:balance", css)
        self.assertIn(".solo .slide p,.solo .slide li,.solo .sc-c{text-wrap:pretty}", css)
        self.assertIn(".solo .cover .cols{grid-template-columns:minmax(0,1fr)}", css, "the next step runs the full column, not half of it")

    def test_the_override_comes_after_the_template_cap(self) -> None:
        page = (Path(__file__).resolve().parents[1] / "examples/acme/decision-record.html").read_text(encoding="utf-8")
        css = page.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertGreater(css.rindex("{max-width:none}"), css.index("max-width:62ch"))


if __name__ == "__main__":
    unittest.main()
