"""Tests for the decision-record scripts. Run: python3 -m unittest discover -s evals -v

Fixtures are Acme, an invented company. Every person, figure and date is illustrative.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "decision-record" / "scripts"
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import declog  # noqa: E402
import open_decisions  # noqa: E402
import record  # noqa: E402
import scan  # noqa: E402

AS_OF = date(2026, 11, 26)


def run_cli(fn, argv: list[str]) -> tuple[int, dict | str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(argv)
    out = buf.getvalue()
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


def rules(findings, level=None) -> set[str]:
    return {f.rule for f in findings if level is None or f.level == level}


def draft(name: str) -> declog.Record:
    return declog.record_from_dict(json.loads((FIX / name).read_text(encoding="utf-8")))


class TestNamedDecider(unittest.TestCase):
    """The rule: a decider is one person's name, or one role scoped to one team ("<role>, <team or squad>")."""

    def test_names_pass(self):
        for n in ["Maya Ortiz", "Maya Ortiz (VP Product)", "Raj", "Lena Brandt-Ruiz", "O'Neill"]:
            self.assertTrue(declog.is_person_name(n), n)
            self.assertTrue(declog.is_named_decider(n), n)

    def test_scoped_roles_pass(self):
        for n in ["Head of Product, Quoting squad", "Lead, Quoting squad", "Tech lead, Quoting squad", "Product manager, Payments team", "VP Engineering, Platform group"]:
            self.assertTrue(declog.is_scoped_role(n), n)
            self.assertTrue(declog.is_named_decider(n), n)
            self.assertFalse(declog.is_person_name(n), n)

    def test_groups_bare_roles_and_blanks_fail(self):
        for n in [
            "the team",
            "We",
            "everyone",
            "Leadership",
            "consensus",
            "TBD",
            "",
            None,
            "Head of Product",
            "Head of Engineering",
            "VP Engineering",
            "the squad",
            "someone in finance",
            "CPO",
        ]:
            self.assertFalse(declog.is_named_decider(n), n)

    def test_unscoped_or_badly_scoped_roles_fail_however_they_are_capitalised(self):
        for n in [
            "Quoting squad lead",  # a role with its team in front, no comma: not the scoped form
            "Quoting Squad Lead",
            "Payments Lead",
            "Lead, the squad",  # a scope with no name of its own
            "Lead, Quoting",  # a scope that is not a team
            "Lead, Quoting squad, Payments team",  # two scopes
            "Maya Ortiz, Quoting squad",  # a name is not a role
            "The team, Quoting squad",
            "TBD, Quoting squad",
            "Lead, TBD squad",
        ]:
            self.assertFalse(declog.is_named_decider(n), n)

    def test_the_validator_uses_the_rule(self):
        src = "Date: 2026-11-12\nHead of Engineering: My call: we ship it.\nLead, Quoting squad: My call: we ship it today.\n"
        base = {"title": "Ship it", "status": "decided", "decision": "Ship it.", "date": "2026-11-12", "source": "notes"}
        bare = declog.record_from_dict({**base, "decided_by": "Head of Engineering", "evidence": "My call: we ship it."})
        self.assertIn("decider-not-a-person", rules(declog.validate(bare, AS_OF, src), "error"))
        scoped = declog.record_from_dict({**base, "decided_by": "Lead, Quoting squad", "evidence": "My call: we ship it today."})
        self.assertEqual(rules(declog.validate(scoped, AS_OF, src), "error"), set())


class TestClearDecision(unittest.TestCase):
    def setUp(self):
        self.src = (FIX / "thread_decided.txt").read_text(encoding="utf-8")

    def test_decided_draft_is_valid_with_no_warnings(self):
        f = declog.validate(draft("draft_decided.json"), AS_OF, self.src)
        self.assertEqual(rules(f, "error"), set())
        self.assertEqual(rules(f, "warning"), set())

    def test_scan_finds_the_call_and_the_decider(self):
        s = scan.scan(self.src)
        self.assertIn("Maya Ortiz", s["speakers"])
        calls = [c for c in s["cues"] if "decision-language" in c["tags"]]
        self.assertTrue(any(c["speaker"] == "Maya Ortiz" and "My call" in c["text"] for c in calls))

    def test_quote_not_in_source_is_refused(self):
        r = draft("draft_decided.json")
        r.evidence = "My call: we auto-send every draft."
        self.assertIn("evidence-not-in-source", rules(declog.validate(r, AS_OF, self.src), "error"))

    def test_decider_absent_from_source_is_refused(self):
        r = draft("draft_decided.json")
        r.decided_by = "Jordan Hale"
        self.assertIn("decider-not-in-source", rules(declog.validate(r, AS_OF, self.src), "error"))

    def test_quote_from_someone_else_warns(self):
        r = draft("draft_decided.json")
        r.evidence = "Got it. It is a settings flag, so easy to switch back if it slows trades down."
        self.assertIn("evidence-from-someone-else", rules(declog.validate(r, AS_OF, self.src), "warning"))

    def test_quote_match_ignores_case_spacing_and_curly_quotes(self):
        r = draft("draft_decided.json")
        r.evidence = "“my call:  WE go with approve before send for every drafted quote.”"
        self.assertNotIn("evidence-not-in-source", rules(declog.validate(r, AS_OF, self.src)))

    def test_decision_date_must_match_the_evidence_line(self):
        r = draft("draft_decided.json")
        r.date = "2026-11-11"
        self.assertIn("date-not-evidence-date", rules(declog.validate(r, AS_OF, self.src), "error"))

    def test_date_header_dates_notes_lines(self):
        src = (FIX / "notes_undecided.txt").read_text(encoding="utf-8")
        utt = declog.parse_source(src)
        self.assertTrue(all(u["date"] == "2026-11-18" for u in utt if u["speaker"]))

    def test_slack_handles_match_the_decider(self):
        src = "[2026-11-12 10:15] @maya.ortiz: My call: approve before send.\n"
        r = draft("draft_decided.json")
        r.evidence = "My call: approve before send."
        f = declog.validate(r, AS_OF, src)
        self.assertNotIn("decider-not-in-source", rules(f))
        self.assertNotIn("evidence-from-someone-else", rules(f))

    def test_assumptions_and_signal_round_trip(self):
        r = draft("draft_decided.json")
        r.id = "D-0001"
        back = declog.parse_log(declog.format_log([r]))[0]
        self.assertEqual(back.assumptions, r.assumptions)
        self.assertEqual(len(back.assumptions), 2)
        self.assertEqual(back.success_signal, r.success_signal)

    def test_chosen_must_be_an_option(self):
        r = draft("draft_decided.json")
        r.chosen = "Auto-send to repeat customers"
        self.assertIn("chosen-not-an-option", rules(declog.validate(r, AS_OF, self.src), "error"))


class TestNoDecision(unittest.TestCase):
    def setUp(self):
        self.src = (FIX / "notes_undecided.txt").read_text(encoding="utf-8")

    def test_overclaim_with_a_group_decider_is_refused(self):
        f = declog.validate(draft("draft_undecided_overclaim.json"), AS_OF, self.src)
        self.assertIn("decider-not-a-person", rules(f, "error"))

    def test_decided_with_no_decider_is_refused(self):
        r = draft("draft_undecided_overclaim.json")
        r.decided_by = None
        self.assertIn("no-decider", rules(declog.validate(r, AS_OF, self.src), "error"))

    def test_decided_with_a_name_that_never_made_the_call_is_refused_by_the_source(self):
        r = draft("draft_undecided_overclaim.json")
        r.decided_by = "Jordan Hale"
        self.assertIn("decider-not-in-source", rules(declog.validate(r, AS_OF, self.src), "error"))

    def test_open_record_is_valid(self):
        f = declog.validate(draft("draft_undecided_open.json"), AS_OF, self.src)
        self.assertEqual(rules(f, "error"), set())

    def test_scan_flags_deferral(self):
        s = scan.scan(self.src)
        self.assertTrue(any("deferred-language" in c["tags"] for c in s["cues"]))
        self.assertIn("2026-11-18", s["dates"])


class TestOtherRules(unittest.TestCase):
    def base(self) -> declog.Record:
        return draft("draft_decided.json")

    def test_future_decision_date(self):
        r = self.base()
        r.date = "2026-12-01"
        self.assertIn("date-in-future", rules(declog.validate(r, AS_OF), "error"))

    def test_bad_date_and_bad_status_and_bad_reversible(self):
        r = self.base()
        r.date, r.status, r.reversible = "12/11/2026", "done", "maybe"
        self.assertTrue({"date-invalid", "status-invalid", "reversible-invalid"} <= rules(declog.validate(r, AS_OF), "error"))

    def test_review_before_decision(self):
        r = self.base()
        r.review_by = "2026-11-01"
        self.assertIn("review-before-decision", rules(declog.validate(r, AS_OF), "error"))

    def test_no_success_signal_warns(self):
        r = self.base()
        r.success_signal = None
        self.assertIn("no-success-signal", rules(declog.validate(r, AS_OF), "warning"))

    def test_worked_needs_a_success_signal(self):
        r = self.base()
        r.success_signal = None
        r.outcome, r.outcome_date, r.outcome_evidence = "worked", "2026-11-25", "Complaints at 3 (illustrative)"
        self.assertIn("worked-without-signal", rules(declog.validate(r, AS_OF), "error"))

    def test_worked_needs_evidence(self):
        r = self.base()
        r.outcome, r.outcome_date = "worked", "2026-11-25"
        self.assertIn("worked-without-evidence", rules(declog.validate(r, AS_OF), "error"))

    def test_only_three_outcome_words(self):
        r = self.base()
        r.outcome, r.outcome_date = "done", "2026-11-25"
        self.assertIn("outcome-invalid", rules(declog.validate(r, AS_OF), "error"))

    def test_outcome_on_open_record(self):
        r = draft("draft_undecided_open.json")
        r.outcome, r.outcome_date, r.outcome_evidence = "pending", "2026-11-25", "x"
        self.assertIn("outcome-on-undecided", rules(declog.validate(r, AS_OF), "error"))

    def test_one_way_door_without_review_warns(self):
        r = self.base()
        r.reversible, r.review_by = "no", None
        self.assertIn("one-way-door-no-review", rules(declog.validate(r, AS_OF), "warning"))

    def test_one_way_door_needs_a_success_signal(self):
        r = self.base()
        r.reversible, r.success_signal = "no", None
        self.assertIn("one-way-door-no-signal", rules(declog.validate(r, AS_OF), "error"))

    def test_drop_needs_reason(self):
        r = declog.Record(id="D-0001", title="x", status="dropped")
        self.assertIn("drop-without-reason", rules(declog.validate(r, AS_OF), "error"))

    def test_open_without_opened_date_warns_and_never_ages(self):
        r = declog.Record(id="D-0001", title="x", status="open", waiting_on="Raj Mehta")
        self.assertIn("no-opened-date", rules(declog.validate(r, AS_OF), "warning"))
        q = declog.open_queue([r], AS_OF)
        self.assertIsNone(q["items"][0]["days_waiting"])


class TestFormat(unittest.TestCase):
    def test_sample_log_round_trips(self):
        text = (FIX / "sample_log.md").read_text(encoding="utf-8")
        recs = declog.parse_log(text)
        self.assertEqual(len(recs), 9)
        self.assertEqual(recs[4].decide_by, "2026-12-02")
        again = declog.parse_log(declog.format_log(recs))
        self.assertEqual([r.to_dict() for r in recs], [r.to_dict() for r in again])

    def test_sample_log_is_valid(self):
        recs = declog.parse_log((FIX / "sample_log.md").read_text(encoding="utf-8"))
        self.assertEqual(rules(declog.validate_log(recs, AS_OF), "error"), set())

    def test_next_id(self):
        self.assertEqual(declog.next_id([]), "D-0001")
        recs = declog.parse_log((FIX / "sample_log.md").read_text(encoding="utf-8"))
        self.assertEqual(declog.next_id(recs), "D-0010")

    def test_text_from_a_thread_cannot_forge_a_record(self):
        r = draft("draft_decided.json")
        r.id = "D-0001"
        r.notes = "fine\n\n## D-0099: Fake\n- Status: decided\n- Decided by: Mallory"
        recs = declog.parse_log(declog.format_log([r]))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].decided_by, "Maya Ortiz")


class TestQueueAndFollowThrough(unittest.TestCase):
    def setUp(self):
        self.recs = declog.parse_log((FIX / "sample_log.md").read_text(encoding="utf-8"))

    def test_usual_days_is_the_median_of_decided_records(self):
        # Days to decide: 7, 11, 9, 3. Median 8.
        self.assertEqual(sorted(declog.days_to_decide(self.recs)), [3, 7, 9, 11])
        self.assertEqual(declog.open_queue(self.recs, AS_OF)["usual_days_to_decide"], 8.0)

    def test_open_items_age_and_on_whom(self):
        q = declog.open_queue(self.recs, AS_OF)
        by = {i["id"]: i for i in q["items"]}
        self.assertEqual([i["id"] for i in q["items"]], ["D-0006", "D-0007", "D-0005", "D-0008"])
        self.assertEqual(by["D-0006"]["days_waiting"], 29)
        self.assertEqual(by["D-0007"]["days_waiting"], 13)
        self.assertEqual(by["D-0005"]["days_waiting"], 8)
        self.assertEqual(by["D-0005"]["waiting_on"], "Raj Mehta")
        self.assertIsNone(by["D-0008"]["waiting_on"])  # a role is not a person
        self.assertIsNone(by["D-0008"]["days_waiting"])

    def test_past_due_and_escalation(self):
        by = {i["id"]: i for i in declog.open_queue(self.recs, AS_OF)["items"]}
        self.assertFalse(by["D-0005"]["past_due"])  # 8 is not more than 8
        self.assertTrue(by["D-0007"]["past_due"])
        self.assertFalse(by["D-0007"]["escalated"])  # someone is named
        self.assertTrue(by["D-0006"]["escalated"])  # 29 > 8 + 14, nobody named

    def test_headline_drops_clauses_that_are_not_true(self):
        q = declog.open_queue(self.recs, AS_OF)
        self.assertEqual(q["headline"], "4 open · oldest 29 days · 2 past due · 2 waiting on nobody named")
        fresh = [declog.Record(id="D-0001", title="x", status="open", opened="2026-11-26", waiting_on="Raj Mehta")]
        self.assertEqual(declog.open_queue(fresh, AS_OF)["headline"], "1 open · all opened today")
        self.assertEqual(declog.open_queue([], AS_OF)["headline"], "No open decisions in the log.")

    def test_no_history_means_nothing_is_past_due(self):
        only_open = [r for r in self.recs if r.status == "open"]
        q = declog.open_queue(only_open, AS_OF)
        self.assertIsNone(q["usual_days_to_decide"])
        self.assertEqual(q["counts"]["past_due"], 0)

    def test_usual_days_override(self):
        q = declog.open_queue(self.recs, AS_OF, expected_days=5)
        self.assertEqual(q["counts"]["past_due"], 3)
        self.assertEqual(q["usual_basis"], "set by the user")

    def test_follow_through(self):
        ft = declog.follow_through(self.recs, AS_OF)
        self.assertEqual((ft["decided"], ft["outcome_read"], ft["not_yet_read"]), (4, 3, 1))
        self.assertEqual((ft["worked"], ft["pending"], ft["missed"]), (1, 1, 1))
        # Three outcomes read is too few for a rate, so none is printed.
        self.assertIsNone(ft["follow_through_rate_pct"])
        self.assertEqual(ft["rate_basis"], "3 outcome(s) read; 5 are needed before a rate means anything")
        self.assertEqual(ft["median_days_to_decide"], 8.0)
        self.assertEqual(ft["without_success_signal"], 0)
        self.assertEqual([r["id"] for r in ft["missed_rows"]], ["D-0002"])
        self.assertEqual(ft["review_due"][0]["id"], "D-0003")
        self.assertEqual(ft["review_due"][0]["days_overdue"], 16)
        self.assertEqual(ft["one_way_doors"], 1)
        self.assertEqual(ft["no_decider_named"], 0)

    def test_rate_appears_at_five_outcomes(self):
        recs = []
        for i, outcome in enumerate(["worked", "worked", "worked", "pending", "missed"], start=1):
            recs.append(declog.Record(id=f"D-{i:04d}", title="x", status="decided", decided_by="Maya Ortiz", date="2026-10-01", outcome=outcome))
        ft = declog.follow_through(recs, AS_OF)
        self.assertEqual(ft["follow_through_rate_pct"], 60)
        self.assertEqual(ft["rate_basis"], "3 worked of 5 decisions with an outcome read")

    def test_median_needs_three_decided_records(self):
        two = [r for r in self.recs if r.id in ("D-0001", "D-0002", "D-0005")]
        q = declog.open_queue(two, AS_OF)
        self.assertIsNone(q["usual_days_to_decide"])
        self.assertIn("3 are needed for a median", q["usual_basis"])
        self.assertEqual(q["counts"]["past_due"], 0)

    def test_review_due_carries_what_to_test(self):
        due = declog.follow_through(self.recs, AS_OF)["review_due"][0]
        self.assertEqual(due["success_signal"], "Audit requests answered in under 1 day (illustrative)")
        code, out = run_cli(open_decisions.main, ["--log", str(FIX / "sample_log.md"), "--as-of", "2026-11-26"])
        self.assertIn("- Test against: Audit requests answered in under 1 day (illustrative)", out)
        self.assertIn("Escalate: past due by more than 14 days with nobody named to make the call.", out)

    def test_follow_through_with_nothing_read_has_no_rate(self):
        self.assertIsNone(declog.follow_through([], AS_OF)["follow_through_rate_pct"])

    def test_open_decisions_cli_markdown(self):
        code, out = run_cli(open_decisions.main, ["--log", str(FIX / "sample_log.md"), "--as-of", "2026-11-26"])
        self.assertEqual(code, 0)
        self.assertIn("| D-0006 | Does the assistant answer customer replies on its own? | 29 | nobody named | escalate |", out)
        self.assertIn("Follow-through: no rate yet (3 outcome(s) read; 5 are needed", out)


class TestRecordCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "decisions.md"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def cli(self, *argv):
        return run_cli(record.main, [str(a) for a in argv])

    def append(self, name, source=None, as_of="2026-11-26"):
        args = ["append", "--draft", FIX / name, "--as-of", as_of, "--log", self.log]
        if source:
            args += ["--source", FIX / source]
        return self.cli(*args)

    def test_append_writes_a_decided_record(self):
        code, out = self.append("draft_decided.json", "thread_decided.txt")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "written")
        recs = declog.parse_log(self.log.read_text(encoding="utf-8"))
        self.assertEqual([r.id for r in recs], ["D-0001"])
        self.assertEqual(recs[0].decided_by, "Maya Ortiz")

    def test_append_refuses_overclaim_and_writes_nothing(self):
        code, out = self.append("draft_undecided_overclaim.json", "notes_undecided.txt")
        self.assertEqual(code, record.REFUSED)
        self.assertEqual(out["result"], "refused")
        self.assertIn("decider-not-a-person", {e["rule"] for e in out["errors"]})
        self.assertFalse(self.log.exists())

    def test_append_keeps_existing_records_byte_for_byte(self):
        self.append("draft_decided.json", "thread_decided.txt")
        before = self.log.read_text(encoding="utf-8")
        code, _ = self.append("draft_undecided_open.json", "notes_undecided.txt")
        self.assertEqual(code, 0)
        after = self.log.read_text(encoding="utf-8")
        self.assertTrue(after.startswith(before))
        self.assertEqual([r.id for r in declog.parse_log(after)], ["D-0001", "D-0002"])

    def test_decide_an_open_record_needs_a_named_person(self):
        self.append("draft_undecided_open.json")
        code, _ = self.cli("decide", "D-0001", "--decided-by", "everyone", "--date", "2026-11-25", "--evidence", "x", "--as-of", "2026-11-26", "--log", self.log)
        self.assertEqual(code, record.REFUSED)
        self.assertEqual(declog.parse_log(self.log.read_text(encoding="utf-8"))[0].status, "open")

    def test_decide_then_outcome(self):
        self.append("draft_undecided_open.json", as_of="2026-11-20")
        notes = self.tmp / "followup.txt"
        notes.write_text("Raj Mehta: Decided: per-trade setting with day 7 as the default.\n", encoding="utf-8")
        code, out = self.cli(
            "decide",
            "D-0001",
            "--decided-by",
            "Raj Mehta",
            "--date",
            "2026-11-25",
            "--evidence",
            "Decided: per-trade setting with day 7 as the default.",
            "--chosen",
            "Per-trade setting, day 7 default",
            "--success-signal",
            "Days sales outstanding no worse than 38 days by 2027-01-15 (illustrative)",
            "--owner",
            "Sam Whitfield",
            "--review-by",
            "2027-01-15",
            "--reversible",
            "yes",
            "--source",
            notes,
            "--as-of",
            "2026-11-26",
            "--log",
            self.log,
        )
        self.assertEqual(code, 0, out)
        r = declog.parse_log(self.log.read_text(encoding="utf-8"))[0]
        self.assertEqual((r.status, r.decided_by, r.waiting_on), ("decided", "Raj Mehta", None))
        self.assertEqual(declog.days_to_decide([r]), [7])
        code, out = self.cli("outcome", "D-0001", "--outcome", "worked", "--date", "2026-11-26", "--as-of", "2026-11-26", "--log", self.log)
        self.assertEqual(code, record.REFUSED)
        self.assertIn("worked-without-evidence", {e["rule"] for e in out["errors"]})
        code, _ = self.cli(
            "outcome",
            "D-0001",
            "--outcome",
            "pending",
            "--date",
            "2026-11-26",
            "--evidence",
            "One day of data (illustrative)",
            "--as-of",
            "2026-11-26",
            "--log",
            self.log,
        )
        self.assertEqual(code, 0)

    def test_drop(self):
        self.append("draft_undecided_open.json")
        code, _ = self.cli("drop", "D-0001", "--because", "Superseded by the billing rebuild.", "--as-of", "2026-11-26", "--log", self.log)
        self.assertEqual(code, 0)
        self.assertEqual(declog.parse_log(self.log.read_text(encoding="utf-8"))[0].status, "dropped")

    def test_adr_export(self):
        out = self.tmp / "adr"
        code, res = self.cli("adr", "--log", FIX / "sample_log.md", "--as-of", "2026-11-26", "--out", out)
        self.assertEqual(code, 0, res)
        files = sorted(p.name for p in out.iterdir())
        self.assertEqual(len(files), 9)
        self.assertEqual(files[0], "d-0001-quote-drafts-use-the-trades-own-price-book.md")
        text = (out / files[0]).read_text(encoding="utf-8")
        self.assertIn("Status: Accepted", text)
        self.assertIn("Decided by Maya Ortiz on 2026-09-08.", text)
        self.assertIn("- Success signal: Quote edit rate below 25% within six weeks (illustrative)", text)

    def test_adr_refuses_an_invalid_log(self):
        self.log.write_text(declog.LOG_HEADER + "\n## D-0001: x\n\n- Status: decided\n- Decided by: the team\n", encoding="utf-8")
        code, _ = self.cli("adr", "--log", self.log, "--as-of", "2026-11-26", "--out", self.tmp / "adr")
        self.assertEqual(code, record.REFUSED)
        self.assertFalse((self.tmp / "adr").exists())

    def test_unknown_id_is_refused(self):
        self.log.write_text(declog.LOG_HEADER, encoding="utf-8")
        code, out = self.cli("drop", "D-0042", "--because", "x", "--as-of", "2026-11-26", "--log", self.log)
        self.assertEqual(code, record.REFUSED)
        self.assertEqual(out["errors"][0]["rule"], "no-such-record")

    def test_validate_sample_log(self):
        code, out = self.cli("validate", "--log", FIX / "sample_log.md", "--as-of", "2026-11-26")
        self.assertEqual(code, 0)
        self.assertEqual(out["result"], "valid")


# The Leader Report's decision format, pinned at its commit 366da9b: the columns intake.py
# imports for decisions, the line draft.py writes on the decision slide, and how render.py
# reads that line back into options. CI runs these; the full round trip below needs the
# Leader Report checked out (LEADER_REPORT, or ~/product-engineering-update).
LR_COLUMNS = ("ask", "options", "recommendation", "deadline")
LR_LINE = re.compile(r"^Options: (?P<options>.+?)\. Deadline: (?P<deadline>.+?)\.$")
LR_SPLIT = re.compile(r",? or ")
LEADER_REPORT = Path(os.environ.get("LEADER_REPORT", Path.home() / "product-engineering-update")) / "skills" / "product-engineering-update" / "scripts"


def lr_slide_line(row: dict) -> str:
    """The line draft.py writes for one decision (draft.py, Drafter.decisions)."""
    return f"Options: {row.get('options') or 'not stated'}. Deadline: {row.get('deadline') or 'not set'}."


class TestLeaderReportExport(unittest.TestCase):
    def setUp(self):
        self.recs = declog.parse_log((FIX / "sample_log.md").read_text(encoding="utf-8"))
        self.rows, self.problems = declog.leader_report_rows(self.recs, AS_OF)
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_open_decisions_only_oldest_first(self):
        self.assertEqual(self.problems, [])
        self.assertEqual([r["id"] for r in self.rows], ["D-0006", "D-0007", "D-0005", "D-0008"])
        self.assertTrue(set(LR_COLUMNS) <= set(declog.LEADER_REPORT_COLUMNS))

    def test_row_content(self):
        by = {r["id"]: r for r in self.rows}
        self.assertEqual(by["D-0005"]["options"], "Keep day 7 for everyone or Per-trade setting, day 7 default")
        self.assertEqual(by["D-0005"]["deadline"], "2026-12-02")
        self.assertEqual(by["D-0005"]["owner"], "Raj Mehta")
        self.assertEqual(by["D-0005"]["recommendation"], "Sam Whitfield recommends the per-trade setting. Waiting on Raj Mehta, 8 days open.")
        self.assertEqual(by["D-0006"]["recommendation"], "No recommendation recorded. Nobody is named to make this call, 29 days open, escalated.")
        self.assertIn("past the usual 8 days to decide", by["D-0007"]["recommendation"])
        self.assertIsNone(by["D-0008"]["deadline"])

    def test_slide_line_parses_back_into_the_same_options(self):
        for row in self.rows:
            m = LR_LINE.match(lr_slide_line(row))
            self.assertIsNotNone(m, row["id"])
            rec = next(r for r in self.recs if r.id == row["id"])
            if rec.options:
                self.assertEqual([o.strip() for o in LR_SPLIT.split(m["options"])], rec.options)

    def test_an_option_with_or_is_refused(self):
        r = next(r for r in self.recs if r.id == "D-0005")
        r.options = ["Day 3 or day 5", "Day 7"]
        _, problems = declog.leader_report_rows(self.recs, AS_OF)
        self.assertEqual([f.rule for f in problems], ["option-splits-on-the-slide"])

    def test_markdown_table_reads_as_the_leader_report_reads_it(self):
        out = self.tmp / "decisions.md"
        code, _ = run_cli(open_decisions.main, ["--log", str(FIX / "sample_log.md"), "--as-of", "2026-11-26", "--leader-report", str(out)])
        self.assertEqual(code, 0)
        lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
        header = [c.strip() for c in lines[0].strip("|").split("|")]
        self.assertEqual(tuple(header[:4]), LR_COLUMNS)
        self.assertEqual(len(lines), 2 + 4)

    def test_csv_export(self):
        out = self.tmp / "decisions.csv"
        code, _ = run_cli(open_decisions.main, ["--log", str(FIX / "sample_log.md"), "--as-of", "2026-11-26", "--leader-report", str(out)])
        self.assertEqual(code, 0)
        rows = list(csv.DictReader(io.StringIO(out.read_text(encoding="utf-8"))))
        self.assertEqual([r["id"] for r in rows], ["D-0006", "D-0007", "D-0005", "D-0008"])
        self.assertEqual(rows[2]["deadline"], "2026-12-02")

    def test_export_refused_for_an_invalid_log(self):
        bad = self.tmp / "bad.md"
        bad.write_text(declog.LOG_HEADER + "\n## D-0001: x\n\n- Status: decided\n- Decided by: the team\n", encoding="utf-8")
        out = self.tmp / "decisions.md"
        with contextlib.redirect_stderr(io.StringIO()):
            code, _ = run_cli(open_decisions.main, ["--log", str(bad), "--as-of", "2026-11-26", "--leader-report", str(out)])
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())

    @unittest.skipUnless((LEADER_REPORT / "validate.py").exists(), "Leader Report not checked out; set LEADER_REPORT")
    def test_round_trip_through_the_leader_report(self):
        """Export, import with intake.py, draft and validate with the Leader Report's own scripts, unchanged."""
        run = self.tmp / "run"
        exported = self.tmp / "decisions.md"
        run_cli(open_decisions.main, ["--log", str(FIX / "sample_log.md"), "--as-of", "2026-11-26", "--leader-report", str(exported)])
        answers = ["--run", str(run), "--company", "Acme", "--period-label", "Q4 2026", "--period-start", "2026-10-01", "--period-end", "2026-12-31"]
        answers += ["--as-of", "2026-11-26", "--gap-owner", "Maya Ortiz", "--gap-due", "2026-12-10", "--no-ask"]

        def lr(script, *args):
            done = subprocess.run([sys.executable, "-B", str(LEADER_REPORT / script), *args], capture_output=True, text=True, timeout=120)  # noqa: S603
            self.assertEqual(done.returncode, 0, f"{script}: {done.stdout}{done.stderr}")
            return done.stdout

        lr("run.py", *answers)
        lr("intake.py", "import", str(run / "intake.json"), "--decisions", str(exported))
        lr("run.py", *answers)
        report = json.loads(lr("validate.py", str(run / "deck.json"), "--json"))
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])
        deck = json.loads((run / "deck.json").read_text(encoding="utf-8"))
        slide = next(s for s in deck["slides"] if s.get("id") == "18")
        self.assertEqual(slide["title"], "4 decisions for you.")
        cards = slide["blocks"][0]["items"]
        self.assertEqual([c["title"] for c in cards], [r["ask"] for r in self.rows])
        invoice = cards[2]
        self.assertEqual(invoice["body"][0], "Sam Whitfield recommends the per-trade setting. Waiting on Raj Mehta, 8 days open.")
        m = LR_LINE.match(invoice["body"][1]["p"])
        self.assertEqual(LR_SPLIT.split(m["options"]), ["Keep day 7 for everyone", "Per-trade setting, day 7 default"])
        self.assertEqual(m["deadline"], "2026-12-02")
        html = (run / "update.html").read_text(encoding="utf-8")
        self.assertIn("Per-trade setting, day 7 default", html)


class TestRepoHygiene(unittest.TestCase):
    # Built from code points so this file does not hold the characters it bans.
    BANNED = [chr(0x2014), "AI-powered", "unlock", "supercharge", "seamless", "robust", "get started", "sign up", "leverage"]

    def files(self):
        for p in ROOT.rglob("*"):
            if (
                p.is_file()
                and ".git" not in p.parts
                and p.suffix in {".md", ".py", ".json", ".txt", ".yml", ".toml", ".html"}
                and p.name != Path(__file__).name
                and "vendor" not in p.parts
            ):
                yield p

    def test_no_banned_words_or_em_dashes(self):
        for p in self.files():
            text = p.read_text(encoding="utf-8").lower()
            for w in self.BANNED:
                self.assertNotIn(w.lower(), text, f"{w!r} in {p.relative_to(ROOT)}")

    def test_versions_agree(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "decision-record" / "SKILL.md").read_text(encoding="utf-8")
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        sys.path.insert(0, str(SCRIPTS))
        import loop

        self.assertEqual(plugin["version"], "0.3.0")
        self.assertIn('version: "0.3.0"', skill)
        self.assertIn('version = "0.3.0"', project)
        self.assertIn("## 0.3.0, 2026-11-26", changelog)
        self.assertEqual(loop.VERSION, "0.3.0")


if __name__ == "__main__":
    unittest.main()
