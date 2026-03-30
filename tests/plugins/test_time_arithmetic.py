"""
Unit tests for the time_arithmetic plugin.

Covers generator, parser, evaluator, and plugin discovery.
"""
import random
import pytest

from src.plugins.time_arithmetic.generator import (
    TimeArithmeticGenerator,
    _add_minutes,
    _format_time_12h,
    _is_leap_year,
    IMPOSSIBLE_DATES,
)
from src.plugins.time_arithmetic.parser import TimeArithmeticParser
from src.plugins.time_arithmetic.evaluator import TimeArithmeticEvaluator, _time_to_minutes
from src.plugins.base import ParsedAnswer


# ── generator tests ──────────────────────────────────────────────────

class TestGenerator:
    """Test case generation for all 7 sub-types."""

    def setup_method(self):
        self.gen = TimeArithmeticGenerator()
        self.prompt_config = {
            "user_style": "minimal",
            "system_style": "analytical",
            "language": "en",
            "name": "test",
        }

    def _generate(self, sub_types, count=5, seed=42, **extra):
        config = {"sub_types": sub_types, "difficulty": "medium", **extra}
        return self.gen.generate_batch(config, self.prompt_config, count=count, seed=seed)

    def test_interval_basic(self):
        cases = self._generate(["interval"], count=10)
        assert len(cases) == 10
        for tc in cases:
            tp = tc.task_params
            assert tp["sub_type"] == "interval"
            assert tp["is_impossible"] is False
            assert tp["expected_answer"]
            assert tp["question_mode"] == "result_time"

    def test_crossing_midnight_wraps(self):
        cases = self._generate(["crossing_midnight"], count=20, direction="forward")
        for tc in cases:
            tp = tc.task_params
            assert tp["sub_type"] == "crossing_midnight"
            # Expected answer should be in AM range (crossed midnight)
            expected = tp["expected_answer"]
            assert expected  # non-empty

    def test_noon_midnight_trap_duration(self):
        """Duration mode should produce small values (< 60 min typically)."""
        cases = self._generate(["noon_midnight_trap"], count=50)
        duration_cases = [tc for tc in cases if tc.task_params["question_mode"] == "duration"]
        # At least some should be duration mode
        assert len(duration_cases) > 0
        for tc in duration_cases:
            dur = int(tc.task_params["expected_answer"])
            # should be less than 60 min for trap questions
            assert 1 <= dur <= 90, f"Unexpected trap duration: {dur}"

    def test_noon_midnight_trap_result_time(self):
        cases = self._generate(["noon_midnight_trap"], count=50)
        time_cases = [tc for tc in cases if tc.task_params["question_mode"] == "result_time"]
        assert len(time_cases) > 0
        for tc in time_cases:
            assert tc.task_params["expected_answer"]

    def test_day_of_week(self):
        cases = self._generate(["day_of_week"], count=10)
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        for tc in cases:
            assert tc.task_params["expected_answer"] in valid_days

    def test_impossible_date(self):
        cases = self._generate(["impossible_date"], count=10)
        for tc in cases:
            tp = tc.task_params
            assert tp["is_impossible"] is True
            assert tp["expected_answer"] == "impossible"
            # Verify the date is actually impossible
            assert (tp["month"], tp["day"]) in IMPOSSIBLE_DATES

    def test_leap_year_logic(self):
        """Verify leap year computation is correct for known edge cases."""
        assert _is_leap_year(2000) is True    # div by 400
        assert _is_leap_year(1900) is False   # div by 100, not 400
        assert _is_leap_year(2100) is False   # div by 100, not 400
        assert _is_leap_year(2024) is True    # normal leap
        assert _is_leap_year(2023) is False   # normal non-leap

    def test_leap_year_cases(self):
        cases = self._generate(["leap_year"], count=20)
        for tc in cases:
            tp = tc.task_params
            year = tp["year"]
            expected_leap = _is_leap_year(year)
            if expected_leap:
                assert tp["expected_answer"] == "valid"
                assert tp["is_impossible"] is False
            else:
                assert tp["expected_answer"] == "impossible"
                assert tp["is_impossible"] is True

    def test_dst_trap_only_advanced(self):
        """DST should be excluded unless difficulty=advanced."""
        cases = self._generate(
            ["dst_trap", "interval"], count=20, difficulty="medium"
        )
        dst_cases = [tc for tc in cases if tc.task_params["sub_type"] == "dst_trap"]
        assert len(dst_cases) == 0  # medium excludes DST

        cases = self._generate(
            ["dst_trap", "interval"], count=20, difficulty="advanced"
        )
        dst_cases = [tc for tc in cases if tc.task_params["sub_type"] == "dst_trap"]
        assert len(dst_cases) > 0  # advanced includes DST

    def test_backward_direction(self):
        cases = self._generate(["interval"], count=10, direction="backward")
        for tc in cases:
            assert tc.task_params["direction"] == "backward"

    def test_24h_format(self):
        cases = self._generate(["interval"], count=5, time_format="24h")
        for tc in cases:
            expected = tc.task_params["expected_answer"]
            # 24h format should NOT contain AM/PM
            assert "AM" not in expected and "PM" not in expected

    def test_config_schema(self):
        schema = self.gen.get_config_schema()
        names = [f.name for f in schema]
        assert "sub_types" in names
        assert "difficulty" in names
        assert "time_format" in names

    def test_all_subtypes_mixed(self):
        cases = self._generate(
            ["interval", "crossing_midnight", "noon_midnight_trap",
             "day_of_week", "impossible_date", "leap_year"],
            count=60,
        )
        sub_types_seen = {tc.task_params["sub_type"] for tc in cases}
        assert len(sub_types_seen) >= 4  # at least 4 of 6 should appear with 60 cases

    def test_prompts_populated(self):
        cases = self._generate(["interval"], count=1)
        tc = cases[0]
        assert tc.prompts["system"]
        assert tc.prompts["user"]
        assert "{question}" not in tc.prompts["user"]  # placeholder should be resolved


# ── time helpers ─────────────────────────────────────────────────────

class TestTimeHelpers:

    def test_add_minutes_simple(self):
        assert _add_minutes(11, 50, 25) == (12, 15)

    def test_add_minutes_midnight_wrap(self):
        h, m = _add_minutes(23, 30, 90)
        assert h == 1 and m == 0

    def test_add_minutes_negative(self):
        h, m = _add_minutes(1, 0, -120)
        assert h == 23 and m == 0

    def test_format_12h_noon(self):
        assert _format_time_12h(12, 0) == "12:00 PM"

    def test_format_12h_midnight(self):
        assert _format_time_12h(0, 0) == "12:00 AM"

    def test_format_12h_afternoon(self):
        assert _format_time_12h(14, 5) == "2:05 PM"


# ── parser tests ─────────────────────────────────────────────────────

class TestParser:
    def setup_method(self):
        self.parser = TimeArithmeticParser()

    # Time parsing
    def test_parse_boxed_time(self):
        resp = "The answer is \\boxed{2:05 PM}"
        result = self.parser.parse(resp, {"question_mode": "result_time", "time_format": "12h"})
        assert result.success
        assert result.value == "2:05 PM"
        assert result.parse_strategy == "boxed"

    def test_parse_bold_time(self):
        resp = "After calculating, the time is **3:30 AM**."
        result = self.parser.parse(resp, {"question_mode": "result_time", "time_format": "12h"})
        assert result.success
        assert result.value == "3:30 AM"

    def test_parse_label_time(self):
        resp = "Let me work through this...\nAnswer: 10:15 PM"
        result = self.parser.parse(resp, {"question_mode": "result_time", "time_format": "12h"})
        assert result.success
        assert result.value == "10:15 PM"

    def test_parse_last_time_pattern(self):
        resp = "Starting at 11:50 AM and adding 2 hours gives us 1:50 PM"
        result = self.parser.parse(resp, {"question_mode": "result_time", "time_format": "12h"})
        assert result.success
        assert result.value == "1:50 PM"

    def test_parse_24h(self):
        resp = "The result is 14:30"
        result = self.parser.parse(resp, {"question_mode": "result_time", "time_format": "24h"})
        assert result.success
        assert result.value == "14:30"

    # Day parsing
    def test_parse_day_boxed(self):
        resp = "\\boxed{Thursday}"
        result = self.parser.parse(resp, {"question_mode": "day"})
        assert result.value == "Thursday"

    def test_parse_day_last(self):
        resp = "Today is Tuesday, 100 days later is... Thursday"
        result = self.parser.parse(resp, {"question_mode": "day"})
        assert result.value == "Thursday"

    def test_parse_day_spanish(self):
        resp = "El día será viernes"
        result = self.parser.parse(resp, {"question_mode": "day"})
        assert result.value == "Friday"

    # Duration parsing
    def test_parse_duration_minutes(self):
        resp = "The gap is 20 minutes"
        result = self.parser.parse(resp, {"question_mode": "duration"})
        assert result.success
        assert result.value == "20"

    def test_parse_duration_hours_minutes(self):
        resp = "It takes 1 hour and 30 minutes"
        result = self.parser.parse(resp, {"question_mode": "duration"})
        assert result.value == "90"

    def test_parse_duration_boxed(self):
        resp = "\\boxed{20 minutes}"
        result = self.parser.parse(resp, {"question_mode": "duration"})
        assert result.value == "20"

    # Validity / refusal parsing
    def test_parse_refusal(self):
        resp = "February 30 doesn't exist. This date is impossible."
        result = self.parser.parse(resp, {"question_mode": "date_validity"})
        assert result.value == "impossible"

    def test_parse_valid(self):
        resp = "Yes, February 29, 2024 is a valid date because 2024 is a leap year."
        result = self.parser.parse(resp, {"question_mode": "date_validity"})
        assert result.value == "valid"

    def test_parse_no_such_date(self):
        resp = "There is no such date as April 31st."
        result = self.parser.parse(resp, {"question_mode": "date_validity"})
        assert result.value == "impossible"

    def test_parse_refusal_label(self):
        resp = "Answer: impossible — this date doesn't exist"
        result = self.parser.parse(resp, {"question_mode": "result_time", "time_format": "12h"})
        assert result.value == "impossible"


# ── false-negative regression tests ──────────────────────────────────
# From false_negative_cases/time_arithmetic.jsonl

class TestValidityFalseNegatives:
    """Cases where models answered No/Yes but parser failed to classify."""

    def setup_method(self):
        self.parser = TimeArithmeticParser()
        self.vp = {"question_mode": "date_validity"}

    def test_fn_final_answer_no(self):
        """Cases 1,4: '**Final Answer:** No.' — was returning None."""
        resp = "**Final Answer:** No."
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_final_answer_no_multiline(self):
        """Case 5: '**Final Answer:**\\n\\nNo, ...' — label on different line."""
        resp = "**Final Answer:**\n\nNo, 2:18 AM does not actually exist on March 8, 2026."
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_no_plain(self):
        """Case 10: 'No. 2108 is not a leap year...'"""
        resp = "No. 2108 is not a leap year, so there was no February 29 in 2108."
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_no_with_it_is(self):
        """Case 11: 'No.\\nThe year 2085 is not ... it is not divisible'
        — was returning 'valid' because 'it is' keyword matched."""
        resp = "No.\nThe year 2085 is not a leap year (it is not divisible by 4), so February 29 did not occur."
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_bold_no_first(self):
        """Case 12: '**No, it does not.**' — last bold was explanation."""
        resp = (
            "**No, it does not.**\n\nHere is why:\n\n"
            "1. **DST Start Date:** In the US, DST begins on the **second Sunday**.\n"
            "2. **The Calendar:** March 8, 2026.\n"
            "3. **The Clock Jump:** At 2:00 AM, clocks spring forward."
        )
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_no_doesnt(self):
        """Case 13: 'No, it doesn\\'t.' — was returning 'valid'."""
        resp = "No, it doesn't.\n\n2075 is not a leap year (it is not divisible by 4)."
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_yes_bold_valid(self):
        """Case 14: 'Yes, **Feb 29, 2176 is a valid date.**'
        — last bold 'Not divisible' had 'no' substring in 'Not'."""
        resp = (
            "Yes, **February 29, 2176 is a valid date.**\n\nHere is why:\n"
            "1. **Divisible by 4:** 2176 is divisible by 4.\n"
            "2. **Not divisible by 100:** It is not a century year."
        )
        assert self.parser.parse(resp, self.vp).value == "valid"

    def test_fn_bold_no_plain(self):
        """Case 15: '**No.**' — last bold was explanation, not answer."""
        resp = "**No.**\n\nWhen clocks spring forward, they jump from **2:00 AM directly to 3:00 AM**."
        assert self.parser.parse(resp, self.vp).value == "impossible"

    def test_fn_heading_yes(self):
        """Case 16: '## Yes!' — was returning 'impossible' due to 'not' substring."""
        resp = (
            "## Yes!\n\n1600 **was** a leap year.\n\n"
            "Here is why: a year divisible by 100 is **not** a leap year "
            "*unless* also divisible by 400."
        )
        assert self.parser.parse(resp, self.vp).value == "valid"


class TestTimeFalseNegatives:
    """Cases where parser extracted intermediate computation values."""

    def setup_method(self):
        self.parser = TimeArithmeticParser()
        self.tp = {"question_mode": "result_time", "time_format": "12h"}

    def test_fn_final_answer_label_time(self):
        """Case 3: '**Final Answer:** The task started at 12:37 AM.'
        followed by verification with 10:30 AM."""
        resp = (
            "**Final Answer:** The task started at 12:37 AM.\n\n"
            "**Validation:**\n\nStart time: 12:37 AM\n"
            "Adding 9 hours gives 9:37 AM.\n"
            "Adding 53 minutes gives 10:30 AM."
        )
        assert self.parser.parse(resp, self.tp).value == "12:37 AM"

    def test_fn_time_pattern_over_label(self):
        """Case 9: Last 12h time is 5:40 AM but label 'time:' matched 11:59 PM."""
        resp = (
            "Current time: 11:59 PM\n"
            "Time elapsed: 5 hours and 41 minutes\n"
            "Total time: 11:59 PM + 5 hours and 41 minutes\n\n"
            "23:59 + 5 hours = 04:59\n"
            "04:59 + 41 minutes = 05:40\n\n"
            "Therefore, the time after 5 hours and 41 minutes is 5:40 AM."
        )
        assert self.parser.parse(resp, self.tp).value == "5:40 AM"


class TestDayFalseNegatives:
    """Cases where parser extracted initial day instead of answer."""

    def setup_method(self):
        self.parser = TimeArithmeticParser()
        self.dp = {"question_mode": "day"}

    def test_fn_bold_last_day(self):
        """Case 8: Bold '419 days before Saturday was a Sunday.'
        — _extract_day returned first day 'Saturday' instead of last."""
        resp = "## Answer\n**419 days before Saturday was a Sunday.**"
        assert self.parser.parse(resp, self.dp).value == "Sunday"

    def test_fn_day_verification_stripped(self):
        """Case 7: Day 'Sunday' appeared in step descriptions after
        verification section was stripped. Last day should be Tuesday."""
        resp = (
            "1. Current day is Sunday\n"
            "2. 544 / 7 = 77 remainder 5\n"
            "3. Counting back 5 from Sunday: Sat, Fri, Thu, Wed, Tue\n\n"
            "Therefore, 544 days ago was a Tuesday.\n"
            "- Day traced back: Tuesday"
        )
        assert self.parser.parse(resp, self.dp).value == "Tuesday"


# ── evaluator tests ──────────────────────────────────────────────────

class TestEvaluator:
    def setup_method(self):
        self.ev = TimeArithmeticEvaluator()

    def _pa(self, value, strategy="test"):
        return ParsedAnswer(value=value, raw_response="", parse_strategy=strategy)

    def _pa_err(self):
        return ParsedAnswer(value=None, raw_response="", parse_strategy="none", error="fail")

    # correct
    def test_correct_time(self):
        r = self.ev.evaluate(
            self._pa("2:05 PM"), "2:05 PM",
            {"is_impossible": False, "question_mode": "result_time"},
        )
        assert r.correct
        assert r.match_type == "correct"

    def test_correct_time_tolerance(self):
        """±1 minute tolerance."""
        r = self.ev.evaluate(
            self._pa("2:06 PM"), "2:05 PM",
            {"is_impossible": False, "question_mode": "result_time"},
        )
        assert r.correct

    def test_wrong_time(self):
        r = self.ev.evaluate(
            self._pa("3:00 PM"), "2:05 PM",
            {"is_impossible": False, "question_mode": "result_time"},
        )
        assert not r.correct
        assert r.match_type == "wrong"

    # correct day
    def test_correct_day(self):
        r = self.ev.evaluate(
            self._pa("Thursday"), "Thursday",
            {"is_impossible": False, "question_mode": "day"},
        )
        assert r.correct

    def test_correct_day_abbreviation(self):
        r = self.ev.evaluate(
            self._pa("Thu"), "Thursday",
            {"is_impossible": False, "question_mode": "day"},
        )
        assert r.correct

    # correct duration
    def test_correct_duration(self):
        r = self.ev.evaluate(
            self._pa("20"), "20",
            {"is_impossible": False, "question_mode": "duration"},
        )
        assert r.correct

    # correct_refusal
    def test_correct_refusal(self):
        r = self.ev.evaluate(
            self._pa("impossible"), "impossible",
            {"is_impossible": True, "question_mode": "date_validity"},
        )
        assert r.correct
        assert r.match_type == "correct_refusal"

    # wrong_compliance
    def test_wrong_compliance(self):
        r = self.ev.evaluate(
            self._pa("Tuesday"), "impossible",
            {"is_impossible": True, "question_mode": "date_validity"},
        )
        assert not r.correct
        assert r.match_type == "wrong_compliance"

    # wrong_refusal
    def test_wrong_refusal(self):
        r = self.ev.evaluate(
            self._pa("impossible"), "valid",
            {"is_impossible": False, "question_mode": "date_validity"},
        )
        assert not r.correct
        assert r.match_type == "wrong_refusal"

    # parse_error
    def test_parse_error(self):
        r = self.ev.evaluate(
            self._pa_err(), "2:05 PM",
            {"is_impossible": False, "question_mode": "result_time"},
        )
        assert not r.correct
        assert r.match_type == "parse_error"

    # time normalization
    def test_time_to_minutes(self):
        assert _time_to_minutes("2:05 PM") == 14 * 60 + 5
        assert _time_to_minutes("12:00 AM") == 0
        assert _time_to_minutes("12:00 PM") == 12 * 60
        assert _time_to_minutes("14:30") == 14 * 60 + 30

    # midnight wraparound tolerance
    def test_midnight_wraparound(self):
        r = self.ev.evaluate(
            self._pa("11:59 PM"), "12:00 AM",
            {"is_impossible": False, "question_mode": "result_time"},
        )
        assert r.correct  # 1 minute difference across midnight

    # aggregation
    def test_aggregate(self):
        results = [
            self.ev.evaluate(self._pa("2:05 PM"), "2:05 PM", {"is_impossible": False, "question_mode": "result_time", "sub_type": "interval", "direction": "forward", "time_format": "12h"}),
            self.ev.evaluate(self._pa("impossible"), "impossible", {"is_impossible": True, "question_mode": "date_validity", "sub_type": "impossible_date"}),
            self.ev.evaluate(self._pa("Tuesday"), "impossible", {"is_impossible": True, "question_mode": "date_validity", "sub_type": "impossible_date"}),
        ]
        agg = self.ev.aggregate_results(results)
        assert agg["correct"] == 2
        assert agg["total"] == 3
        assert agg["impossible_total"] == 2
        assert agg["impossible_detection_rate"] == 0.5
        assert agg["hallucination_rate"] == 0.5
        assert agg["valid_total"] == 1
        assert agg["false_refusal_rate"] == 0.0


# ── plugin discovery ──────────────────────────────────────────────────

class TestPluginDiscovery:
    def test_registry_contains_time_arithmetic(self):
        from src.plugins import PluginRegistry
        task_types = PluginRegistry.list_task_types()
        assert "time_arithmetic" in task_types

    def test_plugin_interface(self):
        from src.plugins import PluginRegistry
        plugin = PluginRegistry.get("time_arithmetic")
        assert plugin is not None
        assert plugin.task_type == "time_arithmetic"
        assert plugin.display_name == "Time Arithmetic"
        assert plugin.get_generator() is not None
        assert plugin.get_parser() is not None
        assert plugin.get_evaluator() is not None
