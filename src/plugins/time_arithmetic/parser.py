"""
Time Arithmetic – Response Parser

Multi-strategy end-first parsing for temporal reasoning answers.
Dispatches by sub_type to extract times, days, durations, or refusal signals.
"""
from __future__ import annotations

import re
from typing import Any, Dict

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import re_search_last

# ── refusal / validity keywords ──────────────────────────────────────

_REFUSAL_KEYWORDS = [
    "doesn't exist", "does not exist", "doesn't exist",
    "impossible", "invalid", "not a valid", "no such date",
    "not a real date", "cannot exist", "can't exist",
    "never existed", "never exists",
    "no existe", "no es válid", "imposible",           # ES
    "n'existe pas", "impossible", "pas valide",         # FR
    "existiert nicht", "ungültig", "unmöglich",         # DE
    "不存在", "无效", "不可能",                            # ZH
    "не існує", "неможлив", "недійсн",                  # UA
]

_VALIDITY_KEYWORDS = [
    "yes", "valid", "exists", "it is", "real date", "it was",
    "is a valid", "is a real", "did exist", "does exist",
    "sí", "válid", "existe",                            # ES
    "oui", "valide", "existe",                          # FR
    "ja", "gültig", "existiert",                        # DE
    "是", "有效", "存在",                                # ZH
    "так", "дійсн", "існує",                           # UA
]

# ── day-of-week names ────────────────────────────────────────────────

_ALL_DAY_NAMES = {
    "monday": "Monday", "mon": "Monday",
    "tuesday": "Tuesday", "tue": "Tuesday", "tues": "Tuesday",
    "wednesday": "Wednesday", "wed": "Wednesday",
    "thursday": "Thursday", "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday",
    "friday": "Friday", "fri": "Friday",
    "saturday": "Saturday", "sat": "Saturday",
    "sunday": "Sunday", "sun": "Sunday",
    # ES
    "lunes": "Monday", "martes": "Tuesday", "miércoles": "Wednesday",
    "jueves": "Thursday", "viernes": "Friday", "sábado": "Saturday", "domingo": "Sunday",
    # FR
    "lundi": "Monday", "mardi": "Tuesday", "mercredi": "Wednesday",
    "jeudi": "Thursday", "vendredi": "Friday", "samedi": "Saturday", "dimanche": "Sunday",
    # DE
    "montag": "Monday", "dienstag": "Tuesday", "mittwoch": "Wednesday",
    "donnerstag": "Thursday", "freitag": "Friday", "samstag": "Saturday", "sonntag": "Sunday",
    # UA
    "понеділок": "Monday", "вівторок": "Tuesday", "середа": "Wednesday",
    "четвер": "Thursday", "п'ятниця": "Friday", "субота": "Saturday", "неділя": "Sunday",
    # ZH
    "星期一": "Monday", "星期二": "Tuesday", "星期三": "Wednesday",
    "星期四": "Thursday", "星期五": "Friday", "星期六": "Saturday", "星期日": "Sunday",
    "周一": "Monday", "周二": "Tuesday", "周三": "Wednesday",
    "周四": "Thursday", "周五": "Friday", "周六": "Saturday", "周日": "Sunday",
}

# Regex to match day names (sorted longest-first to avoid partial matches)
_DAY_PATTERN = re.compile(
    r"\b(" + "|".join(
        re.escape(d) for d in sorted(_ALL_DAY_NAMES.keys(), key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)

# ── time patterns ────────────────────────────────────────────────────

_TIME_12H = re.compile(
    r"(\d{1,2})\s*[:\.]\s*(\d{2})\s*(a\.?m\.?|p\.?m\.?|AM|PM)",
    re.IGNORECASE,
)

_TIME_24H = re.compile(
    r"\b(\d{1,2})\s*[:\.]\s*(\d{2})\b",
)

# Duration: "N minutes", "N hours and M minutes", etc.
_DURATION_PATTERN = re.compile(
    r"(\d+)\s*(?:hours?|hrs?|h)\s*(?:and\s*)?(\d+)\s*(?:minutes?|mins?|m)"
    r"|(\d+)\s*(?:minutes?|mins?|m)"
    r"|(\d+)\s*(?:hours?|hrs?|h)",
    re.IGNORECASE,
)

# Boxed answer
_BOXED = re.compile(r"\\boxed\{([^}]+)\}")
# Bold answer
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
# Label line: "Answer:", "Time:", "Result:", "Day:", "Duration:"
_LABEL = re.compile(
    r"(?:answer|time|result|day|duration|the\s+time\s+is|the\s+answer\s+is|the\s+day\s+is)"
    r"\s*[:=]\s*(.+)",
    re.IGNORECASE,
)

# Pure number (for duration in minutes)
_PURE_NUMBER = re.compile(r"\b(\d{1,5})\b")


class TimeArithmeticParser(ResponseParser):

    def get_strategies(self) -> list[str]:
        return [
            "boxed", "bold", "label_line",
            "time_pattern", "day_pattern",
            "refusal_detection", "date_validity",
            "duration_pattern", "last_sentence_fallback",
        ]

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        sub_type = task_params.get("sub_type", "interval")
        question_mode = task_params.get("question_mode", "result_time")

        if question_mode == "date_validity":
            return self._parse_validity(response)
        if question_mode == "duration":
            return self._parse_duration(response)
        if question_mode == "day":
            return self._parse_day(response)
        # default: result_time
        time_fmt = task_params.get("time_format", "12h")
        return self._parse_time(response, time_fmt)

    # ── validity parsing (impossible_date, leap_year, dst_trap) ──────

    def _parse_validity(self, response: str) -> ParsedAnswer:
        text = response.strip()
        lower = text.lower()

        # Strategy 1: boxed
        m = re_search_last(_BOXED, text)
        if m:
            inner = m.group(1).strip().lower()
            if any(kw in inner for kw in ["no", "impossible", "invalid", "doesn't", "does not", "不存在", "不", "ні"]):
                return ParsedAnswer(value="impossible", raw_response=response, parse_strategy="boxed")
            if any(kw in inner for kw in ["yes", "valid", "exists", "是", "так"]):
                return ParsedAnswer(value="valid", raw_response=response, parse_strategy="boxed")

        # Strategy 2: bold
        m = re_search_last(_BOLD, text)
        if m:
            inner = m.group(1).strip().lower()
            if any(kw in inner for kw in ["no", "impossible", "invalid", "doesn't", "does not"]):
                return ParsedAnswer(value="impossible", raw_response=response, parse_strategy="bold")
            if any(kw in inner for kw in ["yes", "valid", "exists"]):
                return ParsedAnswer(value="valid", raw_response=response, parse_strategy="bold")

        # Strategy 3: refusal keyword scan (end-weighted — check last 500 chars first)
        tail = lower[-500:] if len(lower) > 500 else lower
        for kw in _REFUSAL_KEYWORDS:
            if kw in tail:
                return ParsedAnswer(value="impossible", raw_response=response, parse_strategy="refusal_keyword")

        # Strategy 4: validity keyword scan
        for kw in _VALIDITY_KEYWORDS:
            if kw in tail:
                return ParsedAnswer(value="valid", raw_response=response, parse_strategy="validity_keyword")

        # Strategy 5: full text scan
        for kw in _REFUSAL_KEYWORDS:
            if kw in lower:
                return ParsedAnswer(value="impossible", raw_response=response, parse_strategy="refusal_full")
        for kw in _VALIDITY_KEYWORDS:
            if kw in lower:
                return ParsedAnswer(value="valid", raw_response=response, parse_strategy="validity_full")

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", error="Could not determine validity",
        )

    # ── time parsing ─────────────────────────────────────────────────

    def _parse_time(self, response: str, time_fmt: str) -> ParsedAnswer:
        text = response.strip()

        # Strategy 1: boxed
        m = re_search_last(_BOXED, text)
        if m:
            inner = m.group(1).strip()
            t = self._extract_time_from_str(inner, time_fmt)
            if t:
                return ParsedAnswer(value=t, raw_response=response, parse_strategy="boxed")

        # Strategy 2: bold
        m = re_search_last(_BOLD, text)
        if m:
            inner = m.group(1).strip()
            t = self._extract_time_from_str(inner, time_fmt)
            if t:
                return ParsedAnswer(value=t, raw_response=response, parse_strategy="bold")

        # Strategy 3: label line
        m = re_search_last(_LABEL, text)
        if m:
            inner = m.group(1).strip()
            # Check for refusal in label
            if any(kw in inner.lower() for kw in ["impossible", "doesn't exist", "invalid"]):
                return ParsedAnswer(value="impossible", raw_response=response, parse_strategy="label_refusal")
            t = self._extract_time_from_str(inner, time_fmt)
            if t:
                return ParsedAnswer(value=t, raw_response=response, parse_strategy="label_line")

        # Strategy 4: last time pattern in response
        if time_fmt == "12h":
            m = re_search_last(_TIME_12H, text)
            if m:
                t = self._normalize_12h(m.group(1), m.group(2), m.group(3))
                if t:
                    return ParsedAnswer(value=t, raw_response=response, parse_strategy="time_pattern_12h")

        m = re_search_last(_TIME_24H, text)
        if m:
            h, mn = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mn <= 59:
                if time_fmt == "12h":
                    val = self._to_12h_str(h, mn)
                else:
                    val = f"{h:02d}:{mn:02d}"
                return ParsedAnswer(value=val, raw_response=response, parse_strategy="time_pattern_24h")

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", error="Could not extract time",
        )

    # ── day parsing ──────────────────────────────────────────────────

    def _parse_day(self, response: str) -> ParsedAnswer:
        text = response.strip()

        # Strategy 1: boxed
        m = re_search_last(_BOXED, text)
        if m:
            d = self._extract_day(m.group(1))
            if d:
                return ParsedAnswer(value=d, raw_response=response, parse_strategy="boxed")

        # Strategy 2: bold
        m = re_search_last(_BOLD, text)
        if m:
            d = self._extract_day(m.group(1))
            if d:
                return ParsedAnswer(value=d, raw_response=response, parse_strategy="bold")

        # Strategy 3: label line
        m = re_search_last(_LABEL, text)
        if m:
            d = self._extract_day(m.group(1))
            if d:
                return ParsedAnswer(value=d, raw_response=response, parse_strategy="label_line")

        # Strategy 4: last day name in text
        m = re_search_last(_DAY_PATTERN, text)
        if m:
            d = _ALL_DAY_NAMES.get(m.group(1).lower())
            if d:
                return ParsedAnswer(value=d, raw_response=response, parse_strategy="day_pattern")

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", error="Could not extract day",
        )

    # ── duration parsing (noon_midnight_trap in "duration" mode) ─────

    def _parse_duration(self, response: str) -> ParsedAnswer:
        text = response.strip()

        # Strategy 1: boxed
        m = re_search_last(_BOXED, text)
        if m:
            d = self._extract_minutes(m.group(1))
            if d is not None:
                return ParsedAnswer(value=str(d), raw_response=response, parse_strategy="boxed")

        # Strategy 2: bold
        m = re_search_last(_BOLD, text)
        if m:
            d = self._extract_minutes(m.group(1))
            if d is not None:
                return ParsedAnswer(value=str(d), raw_response=response, parse_strategy="bold")

        # Strategy 3: label line
        m = re_search_last(_LABEL, text)
        if m:
            d = self._extract_minutes(m.group(1))
            if d is not None:
                return ParsedAnswer(value=str(d), raw_response=response, parse_strategy="label_line")

        # Strategy 4: duration pattern
        m = re_search_last(_DURATION_PATTERN, text)
        if m:
            d = self._duration_match_to_minutes(m)
            if d is not None:
                return ParsedAnswer(value=str(d), raw_response=response, parse_strategy="duration_pattern")

        # Strategy 5: last plain number (treat as minutes)
        m = re_search_last(_PURE_NUMBER, text)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 1440:
                return ParsedAnswer(value=str(val), raw_response=response, parse_strategy="last_number", confidence=0.5)

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", error="Could not extract duration",
        )

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_time_from_str(s: str, time_fmt: str) -> str | None:
        """Try to pull a time from a short string."""
        m = _TIME_12H.search(s)
        if m:
            return TimeArithmeticParser._normalize_12h(m.group(1), m.group(2), m.group(3))
        m = _TIME_24H.search(s)
        if m:
            h, mn = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mn <= 59:
                if time_fmt == "12h":
                    return TimeArithmeticParser._to_12h_str(h, mn)
                return f"{h:02d}:{mn:02d}"
        return None

    @staticmethod
    def _normalize_12h(h_str: str, m_str: str, period: str) -> str | None:
        h, m = int(h_str), int(m_str)
        if h < 1 or h > 12 or m < 0 or m > 59:
            return None
        p = period.replace(".", "").upper()
        return f"{h}:{m:02d} {p}"

    @staticmethod
    def _to_12h_str(hour24: int, minute: int) -> str:
        period = "AM" if hour24 < 12 else "PM"
        h = hour24 % 12
        if h == 0:
            h = 12
        return f"{h}:{minute:02d} {period}"

    @staticmethod
    def _extract_day(s: str) -> str | None:
        for word in re.split(r"[\s,.:;]+", s.strip()):
            canonical = _ALL_DAY_NAMES.get(word.lower())
            if canonical:
                return canonical
        return None

    @staticmethod
    def _extract_minutes(s: str) -> int | None:
        """Extract total minutes from a string like '20 minutes', '1 hour 20 min', or plain '20'."""
        m = _DURATION_PATTERN.search(s)
        if m:
            return TimeArithmeticParser._duration_match_to_minutes(m)
        m = _PURE_NUMBER.search(s)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 1440:
                return val
        return None

    @staticmethod
    def _duration_match_to_minutes(m: re.Match) -> int | None:
        if m.group(1) and m.group(2):  # hours + minutes
            return int(m.group(1)) * 60 + int(m.group(2))
        if m.group(3):  # minutes only
            return int(m.group(3))
        if m.group(4):  # hours only
            return int(m.group(4)) * 60
        return None
