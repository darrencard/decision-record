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

import declog  # noqa: E402
import from_thread  # noqa: E402
import landing_brief  # noqa: E402
import loop  # noqa: E402
import open_decisions  # noqa: E402
import render_html  # noqa: E402

BET = "quote-drafting"
AS_OF = "2026-07-27"
STATUS_WORDS = re.compile(r"\b(landed|watch|stalled)\b", re.I)
SAMPLE_OUTPUTS = (
    "decisions.md", "decision-record.html", "decision-record.md", "leader-report-decisions.md", f"landing/{BET}.json",
    "later/decisions.md", "later/open-decisions.md",
)  # fmt: skip


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
    """The Decide-step snapshot and the later read tell one story with the rest of the loop."""

    def test_the_decide_snapshot_comes_before_spec_and_shows_both_calls_open(self):
        rec = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["decisions"]["as_of"], AS_OF)
        self.assertLess(rec["decisions"]["as_of"], "2026-08-03")  # 02 Spec reads on 2026-08-03
        self.assertEqual([r["id"] for r in rec["decisions"]["rows"]], ["D-0004", "D-0005"])

    def test_the_later_log_decides_the_trigger_before_release_and_the_tier_before_the_cost_read(self):
        recs = {r.id: r for r in declog.parse_log((ACME / "later" / "decisions.md").read_text(encoding="utf-8"))}
        self.assertEqual({r.status for r in recs.values()}, {"decided"})
        trigger, tier = recs["D-0004"], recs["D-0005"]
        self.assertEqual((trigger.decided_by, trigger.owner), ("Head of Product, Quoting squad", "Tech lead, Quoting squad"))
        self.assertEqual(trigger.chosen, "Roll back when wrong-price quotes pass 2%")
        self.assertTrue("2026-08-03" < trigger.date < "2026-09-05")  # after the spec hold, before the release read
        self.assertLess(tier.date, "2026-11-15")  # before the cost read
        self.assertEqual(tier.chosen, "vendor-a/m")
        for r in (trigger, tier):
            self.assertEqual(r.source, "Acme spec review call, 2026-08-10 (illustrative)")
        self.assertEqual(declog.validate_log(list(recs.values()), date(2026, 11, 26)), [])
        self.assertIn("No open decisions in the log.", (ACME / "later" / "open-decisions.md").read_text(encoding="utf-8"))

    def test_the_readme_shows_the_later_read(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("--log examples/acme/later/decisions.md --as-of 2026-11-26", readme)

    def test_past_due_means_a_passed_deadline_not_a_long_wait(self):
        md = (ACME / "decision-record.md").read_text(encoding="utf-8")
        self.assertIn("1 waiting longer than usual: D-0004 has waited 14 days on Lead, Quoting squad, against a usual 7.", md)
        self.assertNotIn("past due", md)  # D-0004's deadline, 2026-08-03, is still ahead on 2026-07-27
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        late = json.loads(json.dumps(key))
        late["as_of"] = "2026-08-04"
        self.assertIn("2 past due: D-0004 was to be decided by 2026-08-03.", render_html.lede(late))


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
            shutil.copy(ACME / "decisions.md", log)
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
        self.assertEqual(key["next_step_by"], "Lead, Quoting squad")


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
        got = {k: f[k]["value"] for k in ("open", "decided", "waiting_long", "past_due", "oldest_open", "usual_days_to_decide")}
        # D-0004 has waited 14 days against a usual 7, but its decide-by date (2026-08-03) is still ahead: not past due.
        self.assertEqual(got, {"open": 2, "decided": 3, "waiting_long": 1, "past_due": 0, "oldest_open": 14, "usual_days_to_decide": 7.0})


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
        for r in key["rows"]:
            self.assertEqual(list(r), key["columns"])
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
        self.assertIn('<span class="ill">Illustrative</span>', self.body)

    def test_selection_and_focus_ring_are_ink_not_green(self):
        css = self.html[self.html.index("::selection{background:var(--t1)") :]
        self.assertIn(":focus-visible{outline-color:var(--t1)}", css)
        self.assertNotIn("var(--landed)", css)

    def test_no_status_colour_and_brass_only_for_a_persons_call(self):
        self.assertNotIn('class="st', self.body)
        self.assertNotIn("var(--landed)", self.body)
        self.assertNotIn("var(--stalled)", self.body)
        brass = re.findall(r'<span class="who">([^<]*)</span>', self.body)
        self.assertEqual(set(brass), {"Head of Product, Quoting squad", "Tech lead, Quoting squad", "Lead, Quoting squad"})
        # The brand mark's brass bar, and the next step's named person. Nothing else.
        self.assertEqual(self.body.count("var(--brass)"), 2)

    def test_source_text_is_escaped(self):
        key = json.loads((ACME / "landing" / f"{BET}.json").read_text(encoding="utf-8"))["decisions"]
        key = json.loads(json.dumps(key))
        key["rows"][0]["ask"] = "<script>alert(1)</script>"
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


if __name__ == "__main__":
    unittest.main()
