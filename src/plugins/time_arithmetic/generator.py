"""
Time Arithmetic – Test Case Generator

Generates temporal reasoning questions across 7 sub-types with
configurable difficulty, direction, time format, and trick-question
inclusion.
"""
from __future__ import annotations

import calendar
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.PromptEngine import Language
from src.plugins.base import ConfigField, TestCase, TestCaseGenerator
from src.plugins.parse_utils import safe_enum
from src.plugins.time_arithmetic.prompts import USER_PROMPT_TEMPLATES

# ── constants ────────────────────────────────────────────────────────

ALL_SUB_TYPES = [
    "interval",
    "crossing_midnight",
    "noon_midnight_trap",
    "day_of_week",
    "impossible_date",
    "leap_year",
    "dst_trap",
]

DEFAULT_SUB_TYPES = [s for s in ALL_SUB_TYPES if s != "dst_trap"]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MONTHS_30 = {4, 6, 9, 11}  # Apr, Jun, Sep, Nov
MONTHS_31 = {1, 3, 5, 7, 8, 10, 12}

# Impossible (month, day) pairs that never exist
IMPOSSIBLE_DATES = [
    (2, 30), (2, 31),
    (4, 31), (6, 31), (9, 31), (11, 31),
]

# Leap-year test years: (year, is_leap)
LEAP_YEAR_POOL = [
    # Normal leap years
    (2024, True), (2028, True), (2032, True), (2020, True), (2016, True),
    (1996, True), (1984, True), (1600, True), (2400, True),
    # Century non-leap (div by 100, NOT by 400)
    (1900, False), (2100, False), (2200, False), (2300, False),
    (1800, False), (1700, False),
    # Century leap (div by 400)
    (2000, True), (1600, True),
    # Normal non-leap
    (2023, False), (2025, False), (2019, False), (2101, False),
    (1999, False), (1901, False),
]

# DST spring-forward holes (US): clocks skip 2:00→3:00 AM on 2nd Sunday of March
DST_SPRING_FORWARD = [
    # (year, month, day, description)
    (2024, 3, 10, "March 10, 2024"),
    (2025, 3, 9, "March 9, 2025"),
    (2026, 3, 8, "March 8, 2026"),
    (2023, 3, 12, "March 12, 2023"),
]

# ── multilingual question templates ──────────────────────────────────
# Each sub-type has a dict mapping Language → list of template strings.
# The generator picks one at random.

_INTERVAL_TEMPLATES = {
    Language.EN: [
        "It's {start}. If you wait {dur}, what time will it be?",
        "The current time is {start}. What time is it after {dur}?",
        "Starting at {start}, add {dur}. What's the resulting time?",
    ],
    Language.ES: [
        "Son las {start}. Si esperas {dur}, ¿qué hora será?",
        "La hora actual es {start}. ¿Qué hora será después de {dur}?",
    ],
    Language.FR: [
        "Il est {start}. Si vous attendez {dur}, quelle heure sera-t-il ?",
        "L'heure actuelle est {start}. Quelle heure sera-t-il après {dur} ?",
    ],
    Language.DE: [
        "Es ist {start}. Wenn du {dur} wartest, wie spät ist es dann?",
        "Die aktuelle Uhrzeit ist {start}. Wie spät ist es nach {dur}?",
    ],
    Language.ZH: [
        "现在是{start}。等待{dur}之后是几点？",
        "当前时间是{start}。{dur}后是几点？",
    ],
    Language.UA: [
        "Зараз {start}. Якщо почекати {dur}, котра буде година?",
        "Поточний час — {start}. Котра година буде через {dur}?",
    ],
}

_INTERVAL_BACKWARD_TEMPLATES = {
    Language.EN: [
        "A meeting ended at {start} and lasted {dur}. When did it start?",
        "It's {start} now. What time was it {dur} ago?",
        "The event finished at {start} after running for {dur}. What was the start time?",
    ],
    Language.ES: [
        "Una reunión terminó a las {start} y duró {dur}. ¿Cuándo empezó?",
        "Son las {start}. ¿Qué hora era hace {dur}?",
    ],
    Language.FR: [
        "Une réunion s'est terminée à {start} et a duré {dur}. Quand a-t-elle commencé ?",
        "Il est {start}. Quelle heure était-il il y a {dur} ?",
    ],
    Language.DE: [
        "Ein Meeting endete um {start} und dauerte {dur}. Wann hat es begonnen?",
        "Es ist {start}. Wie spät war es vor {dur}?",
    ],
    Language.ZH: [
        "会议在{start}结束，持续了{dur}。它几点开始？",
        "现在是{start}。{dur}之前是几点？",
    ],
    Language.UA: [
        "Зустріч закінчилась о {start} і тривала {dur}. Коли вона почалась?",
        "Зараз {start}. Котра година була {dur} тому?",
    ],
}

_CROSSING_MIDNIGHT_TEMPLATES = {
    Language.EN: [
        "You start a task at {start} that takes {dur}. What time do you finish?",
        "It's {start}. After {dur}, what time is it?",
        "A job begins at {start} and runs for {dur}. When does it end?",
    ],
    Language.ES: [
        "Comienzas una tarea a las {start} que toma {dur}. ¿A qué hora terminas?",
    ],
    Language.FR: [
        "Vous commencez une tâche à {start} qui prend {dur}. À quelle heure finissez-vous ?",
    ],
    Language.DE: [
        "Du beginnst um {start} eine Aufgabe, die {dur} dauert. Wann bist du fertig?",
    ],
    Language.ZH: [
        "你在{start}开始一项任务，需要{dur}。你几点完成？",
    ],
    Language.UA: [
        "Ви починаєте завдання о {start}, яке займає {dur}. О котрій закінчите?",
    ],
}

_CROSSING_MIDNIGHT_BACKWARD_TEMPLATES = {
    Language.EN: [
        "You finished a task at {start} that took {dur}. When did you start?",
        "It's {start} now. What time was it {dur} ago?",
    ],
    Language.ES: [
        "Terminaste una tarea a las {start} que tardó {dur}. ¿Cuándo empezaste?",
    ],
    Language.FR: [
        "Vous avez terminé une tâche à {start} qui a pris {dur}. Quand avez-vous commencé ?",
    ],
    Language.DE: [
        "Du hast um {start} eine Aufgabe beendet, die {dur} gedauert hat. Wann hast du angefangen?",
    ],
    Language.ZH: [
        "你在{start}完成了一项耗时{dur}的任务。你几点开始的？",
    ],
    Language.UA: [
        "Ви закінчили завдання о {start}, яке зайняло {dur}. Коли почали?",
    ],
}

_NOON_TRAP_DURATION_TEMPLATES = {
    Language.EN: [
        "How many minutes is it from {start} to {end}?",
        "What is the duration from {start} to {end}?",
        "How long is the gap between {start} and {end}?",
    ],
    Language.ES: [
        "¿Cuántos minutos hay de {start} a {end}?",
    ],
    Language.FR: [
        "Combien de minutes y a-t-il de {start} à {end} ?",
    ],
    Language.DE: [
        "Wie viele Minuten liegen zwischen {start} und {end}?",
    ],
    Language.ZH: [
        "从{start}到{end}有多少分钟？",
    ],
    Language.UA: [
        "Скільки хвилин від {start} до {end}?",
    ],
}

_NOON_TRAP_RESULT_TEMPLATES = {
    Language.EN: [
        "It's {start}. What time will it be in {dur}?",
        "The time is {start}. After {dur}, what's the time?",
    ],
    Language.ES: [
        "Son las {start}. ¿Qué hora será en {dur}?",
    ],
    Language.FR: [
        "Il est {start}. Quelle heure sera-t-il dans {dur} ?",
    ],
    Language.DE: [
        "Es ist {start}. Wie spät ist es in {dur}?",
    ],
    Language.ZH: [
        "现在{start}。{dur}后几点？",
    ],
    Language.UA: [
        "Зараз {start}. Котра буде через {dur}?",
    ],
}

_DAY_OF_WEEK_TEMPLATES = {
    Language.EN: [
        "Today is {day}. What day of the week will it be in {n} days?",
        "If today is {day}, what day is it {n} days from now?",
        "Starting from {day}, count forward {n} days. What day is it?",
    ],
    Language.ES: [
        "Hoy es {day}. ¿Qué día de la semana será en {n} días?",
    ],
    Language.FR: [
        "Aujourd'hui c'est {day}. Quel jour de la semaine sera-t-il dans {n} jours ?",
    ],
    Language.DE: [
        "Heute ist {day}. Welcher Wochentag ist in {n} Tagen?",
    ],
    Language.ZH: [
        "今天是{day}。{n}天后是星期几？",
    ],
    Language.UA: [
        "Сьогодні {day}. Який день тижня буде через {n} днів?",
    ],
}

_DAY_OF_WEEK_BACKWARD_TEMPLATES = {
    Language.EN: [
        "Today is {day}. What day of the week was it {n} days ago?",
        "If today is {day}, what day was it {n} days before?",
    ],
    Language.ES: [
        "Hoy es {day}. ¿Qué día de la semana fue hace {n} días?",
    ],
    Language.FR: [
        "Aujourd'hui c'est {day}. Quel jour de la semaine était-il il y a {n} jours ?",
    ],
    Language.DE: [
        "Heute ist {day}. Welcher Wochentag war vor {n} Tagen?",
    ],
    Language.ZH: [
        "今天是{day}。{n}天前是星期几？",
    ],
    Language.UA: [
        "Сьогодні {day}. Який день тижня був {n} днів тому?",
    ],
}

_IMPOSSIBLE_DATE_TEMPLATES = {
    Language.EN: [
        "What day of the week is {date}?",
        "Can you tell me what day {date} falls on?",
        "On which weekday does {date} occur?",
    ],
    Language.ES: [
        "¿Qué día de la semana es el {date}?",
    ],
    Language.FR: [
        "Quel jour de la semaine est le {date} ?",
    ],
    Language.DE: [
        "Welcher Wochentag ist der {date}?",
    ],
    Language.ZH: [
        "{date}是星期几？",
    ],
    Language.UA: [
        "Який день тижня {date}?",
    ],
}

_LEAP_YEAR_TEMPLATES = {
    Language.EN: [
        "Is February 29, {year} a valid date?",
        "Does February 29 exist in the year {year}?",
        "Was there a February 29 in {year}?",
    ],
    Language.ES: [
        "¿Es el 29 de febrero de {year} una fecha válida?",
    ],
    Language.FR: [
        "Le 29 février {year} est-il une date valide ?",
    ],
    Language.DE: [
        "Ist der 29. Februar {year} ein gültiges Datum?",
    ],
    Language.ZH: [
        "{year}年2月29日是一个有效日期吗？",
    ],
    Language.UA: [
        "Чи є 29 лютого {year} дійсною датою?",
    ],
}

_DST_TEMPLATES = {
    Language.EN: [
        "In the US, on {date}, does {time} actually exist? (Hint: daylight saving time)",
        "Clocks spring forward on {date} in the US. Does {time} exist that day?",
    ],
    Language.ES: [
        "En EE.UU., el {date}, ¿existe realmente las {time}? (Pista: horario de verano)",
    ],
    Language.FR: [
        "Aux États-Unis, le {date}, {time} existe-t-il vraiment ? (Indice : heure d'été)",
    ],
    Language.DE: [
        "In den USA, existiert am {date} die Uhrzeit {time}? (Hinweis: Sommerzeit)",
    ],
    Language.ZH: [
        "在美国，{date}那天{time}实际存在吗？（提示：夏令时）",
    ],
    Language.UA: [
        "У США, чи існує {time} {date}? (Підказка: перехід на літній час)",
    ],
}

# Day translations for day_of_week questions
_DAYS_I18N = {
    Language.EN: DAYS,
    Language.ES: ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
    Language.FR: ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
    Language.DE: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    Language.ZH: ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
    Language.UA: ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "субота", "неділя"],
}

# Month name lookup for impossible-date questions
_MONTH_NAMES = {
    Language.EN: {2: "February", 4: "April", 6: "June", 9: "September", 11: "November"},
    Language.ES: {2: "febrero", 4: "abril", 6: "junio", 9: "septiembre", 11: "noviembre"},
    Language.FR: {2: "février", 4: "avril", 6: "juin", 9: "septembre", 11: "novembre"},
    Language.DE: {2: "Februar", 4: "April", 6: "Juni", 9: "September", 11: "November"},
    Language.ZH: {2: "2月", 4: "4月", 6: "6月", 9: "9月", 11: "11月"},
    Language.UA: {2: "лютого", 4: "квітня", 6: "червня", 9: "вересня", 11: "листопада"},
}


# ── helpers ──────────────────────────────────────────────────────────

def _is_leap_year(year: int) -> bool:
    return calendar.isleap(year)


def _format_time_12h(hour: int, minute: int) -> str:
    """Format (hour, minute) as '2:05 PM'. Hour is 0-23."""
    period = "AM" if hour < 12 else "PM"
    display_h = hour % 12
    if display_h == 0:
        display_h = 12
    return f"{display_h}:{minute:02d} {period}"


def _format_time_24h(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _format_time(hour: int, minute: int, fmt: str) -> str:
    if fmt == "24h":
        return _format_time_24h(hour, minute)
    return _format_time_12h(hour, minute)


def _format_duration(total_minutes: int) -> str:
    """Human-readable duration: '2 hours and 25 minutes', '45 minutes', etc."""
    h, m = divmod(total_minutes, 60)
    if h and m:
        return f"{h} hour{'s' if h != 1 else ''} and {m} minute{'s' if m != 1 else ''}"
    if h:
        return f"{h} hour{'s' if h != 1 else ''}"
    return f"{m} minute{'s' if m != 1 else ''}"


def _add_minutes(hour: int, minute: int, delta: int) -> tuple[int, int]:
    """Add *delta* minutes (may be negative). Returns (hour % 24, minute)."""
    total = hour * 60 + minute + delta
    total %= 1440  # wrap within 24h
    return divmod(total, 60)


# ── difficulty presets ───────────────────────────────────────────────

_DIFFICULTY = {
    "easy": {"max_dur_h": 4, "max_day_offset": 30, "include_dst": False},
    "medium": {"max_dur_h": 8, "max_day_offset": 200, "include_dst": False},
    "hard": {"max_dur_h": 12, "max_day_offset": 1000, "include_dst": False},
    "advanced": {"max_dur_h": 18, "max_day_offset": 1000, "include_dst": True},
}


# ── generator ────────────────────────────────────────────────────────

class TimeArithmeticGenerator(TestCaseGenerator):

    # ── config schema (for web UI) ───────────────────────────────────

    def get_config_schema(self) -> list[ConfigField]:
        return [
            ConfigField(
                name="count", label="Number of cases",
                field_type="number", default=100,
                min_value=1, max_value=500,
                help="Cases to generate per prompt configuration.",
            ),
            ConfigField(
                name="sub_types", label="Sub-types",
                field_type="multi-select", default=DEFAULT_SUB_TYPES,
                options=ALL_SUB_TYPES,
                help="Which question categories to include.",
            ),
            ConfigField(
                name="sub_type_weights", label="Sub-type weights",
                field_type="weight_map", default=None,
                weight_keys=ALL_SUB_TYPES,
                help="Relative frequency for each sub-type (equal if omitted).",
            ),
            ConfigField(
                name="include_trick_questions", label="Include trick questions",
                field_type="boolean", default=True,
                help="Include impossible_date & leap_year sub-types.",
            ),
            ConfigField(
                name="direction", label="Direction",
                field_type="select", default="both",
                options=["forward", "backward", "both"],
                help="Forward (add), backward (subtract), or both.",
            ),
            ConfigField(
                name="time_format", label="Time format",
                field_type="select", default="12h",
                options=["12h", "24h"],
                help="12-hour (AM/PM) or 24-hour display.",
            ),
            ConfigField(
                name="difficulty", label="Difficulty",
                field_type="select", default="medium",
                options=["easy", "medium", "hard", "advanced"],
                help="Controls duration ranges, day offsets, and DST inclusion.",
            ),
            ConfigField(
                name="max_duration_hours", label="Max duration (hours)",
                field_type="number", default=12,
                min_value=1, max_value=48, step=1,
                group="advanced",
                help="Cap on randomly generated durations.",
            ),
            ConfigField(
                name="year_range_start", label="Year range start",
                field_type="number", default=1900,
                min_value=1, max_value=3000, step=1, group="advanced",
            ),
            ConfigField(
                name="year_range_end", label="Year range end",
                field_type="number", default=2200,
                min_value=1, max_value=3000, step=1, group="advanced",
            ),
        ]

    def get_default_config(self) -> dict[str, Any]:
        return {
            "sub_types": DEFAULT_SUB_TYPES,
            "sub_type_weights": None,
            "include_trick_questions": True,
            "direction": "both",
            "time_format": "12h",
            "difficulty": "medium",
            "max_duration_hours": 12,
            "year_range_start": 1900,
            "year_range_end": 2200,
        }

    # ── main entry ───────────────────────────────────────────────────

    def generate_batch(
        self,
        config: dict[str, Any],
        prompt_config: dict[str, str],
        count: int,
        seed: int | None = None,
    ) -> list[TestCase]:
        rng = random.Random(seed)
        cfg = {**self.get_default_config(), **config}

        difficulty = cfg.get("difficulty", "medium")
        diff = _DIFFICULTY.get(difficulty, _DIFFICULTY["medium"])
        max_dur_h = min(cfg.get("max_duration_hours", 12), diff["max_dur_h"])
        max_day_offset = diff["max_day_offset"]

        # Resolve sub-types
        sub_types: list[str] = list(cfg.get("sub_types", DEFAULT_SUB_TYPES))
        if not cfg.get("include_trick_questions", True):
            sub_types = [s for s in sub_types if s not in ("impossible_date", "leap_year")]
        if not diff["include_dst"]:
            sub_types = [s for s in sub_types if s != "dst_trap"]
        if not sub_types:
            sub_types = ["interval"]

        # Weights
        raw_weights = cfg.get("sub_type_weights") or {}
        weights = [float(raw_weights.get(s, 1.0)) for s in sub_types]

        # Prompt metadata
        lang = safe_enum(Language, prompt_config.get("language", "en"), Language.EN)
        user_style = prompt_config.get("user_style", "minimal")
        sys_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", f"{user_style}_{sys_style}")

        time_fmt = cfg.get("time_format", "12h")
        direction = cfg.get("direction", "both")
        year_range = (cfg.get("year_range_start", 1900), cfg.get("year_range_end", 2200))

        test_cases: list[TestCase] = []
        for i in range(count):
            st = rng.choices(sub_types, weights=weights, k=1)[0]
            tc = self._dispatch_generate(
                rng, st,
                lang=lang, user_style=user_style, sys_style=sys_style,
                config_name=config_name,
                time_fmt=time_fmt, direction=direction,
                max_dur_h=max_dur_h, max_day_offset=max_day_offset,
                year_range=year_range, index=i, seed=seed,
            )
            test_cases.append(tc)

        return test_cases

    # ── dispatch ─────────────────────────────────────────────────────

    _GENERATORS: dict[str, str] = {
        "interval": "_gen_interval",
        "crossing_midnight": "_gen_crossing_midnight",
        "noon_midnight_trap": "_gen_noon_midnight_trap",
        "day_of_week": "_gen_day_of_week",
        "impossible_date": "_gen_impossible_date",
        "leap_year": "_gen_leap_year",
        "dst_trap": "_gen_dst_trap",
    }

    def _dispatch_generate(self, rng, sub_type, **kw) -> TestCase:
        method_name = self._GENERATORS.get(sub_type, "_gen_interval")
        return getattr(self, method_name)(rng, sub_type=sub_type, **kw)

    # ── interval ─────────────────────────────────────────────────────

    def _gen_interval(self, rng: random.Random, *, sub_type, lang, user_style,
                      sys_style, config_name, time_fmt, direction,
                      max_dur_h, index, seed, **_kw) -> TestCase:
        hour = rng.randint(0, 23)
        minute = rng.randint(0, 59)
        dur_min = rng.randint(1, max(1, max_dur_h * 60))

        backward = direction == "backward" or (direction == "both" and rng.random() < 0.5)
        delta = -dur_min if backward else dur_min
        res_h, res_m = _add_minutes(hour, minute, delta)

        start_str = _format_time(hour, minute, time_fmt)
        dur_str = _format_duration(dur_min)
        expected = _format_time(res_h, res_m, time_fmt)

        templates = _INTERVAL_BACKWARD_TEMPLATES if backward else _INTERVAL_TEMPLATES
        question = rng.choice(templates.get(lang, templates[Language.EN])).format(
            start=start_str, dur=dur_str,
        )

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "start_time": start_str,
                "duration": dur_str,
                "duration_minutes": dur_min,
                "direction": "backward" if backward else "forward",
                "expected_answer": expected,
                "is_impossible": False,
                "time_format": time_fmt,
                "question_mode": "result_time",
            },
        )

    # ── crossing midnight ────────────────────────────────────────────

    def _gen_crossing_midnight(self, rng: random.Random, *, sub_type, lang,
                               user_style, sys_style, config_name,
                               time_fmt, direction, max_dur_h, index, seed,
                               **_kw) -> TestCase:
        backward = direction == "backward" or (direction == "both" and rng.random() < 0.5)

        if backward:
            # Result in AM, start crosses back past midnight into PM of prev day
            res_h = rng.randint(0, 5)   # result in early AM
            res_m = rng.randint(0, 59)
            # Duration must push us past midnight backward → into PM
            min_dur = res_h * 60 + res_m + 1  # at least past midnight
            max_dur = min(max_dur_h * 60, 1440 - 1)
            if min_dur >= max_dur:
                min_dur = 1
            dur_min = rng.randint(min_dur, max(min_dur, max_dur))
            start_h, start_m = _add_minutes(res_h, res_m, dur_min)  # start = result + dur
            expected = _format_time(res_h, res_m, time_fmt)
            start_str = _format_time(start_h, start_m, time_fmt)
        else:
            # Start in PM evening, duration pushes past midnight
            hour = rng.randint(20, 23)
            minute = rng.randint(0, 59)
            remaining_to_midnight = (24 - hour) * 60 - minute
            min_dur = remaining_to_midnight + 1
            max_dur = min(max_dur_h * 60, 1440 - 1)
            if min_dur >= max_dur:
                max_dur = min_dur + 60
            dur_min = rng.randint(min_dur, max(min_dur, max_dur))
            res_h, res_m = _add_minutes(hour, minute, dur_min)
            start_str = _format_time(hour, minute, time_fmt)
            expected = _format_time(res_h, res_m, time_fmt)

        dur_str = _format_duration(dur_min)
        templates = _CROSSING_MIDNIGHT_BACKWARD_TEMPLATES if backward else _CROSSING_MIDNIGHT_TEMPLATES
        question = rng.choice(templates.get(lang, templates[Language.EN])).format(
            start=start_str, dur=dur_str,
        )

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "start_time": start_str,
                "duration": dur_str,
                "duration_minutes": dur_min,
                "direction": "backward" if backward else "forward",
                "expected_answer": expected,
                "is_impossible": False,
                "time_format": time_fmt,
                "question_mode": "result_time",
            },
        )

    # ── noon / midnight trap ─────────────────────────────────────────

    def _gen_noon_midnight_trap(self, rng: random.Random, *, sub_type, lang,
                                user_style, sys_style, config_name,
                                time_fmt, index, seed, **_kw) -> TestCase:
        # Two trap scenarios:
        #   A) 11:XX AM → 12:XX PM  (noon crossing)
        #   B) 11:XX PM → 12:XX AM  (midnight crossing)
        noon_trap = rng.random() < 0.5

        if noon_trap:
            start_h = 11   # 11 AM
            start_m = rng.randint(30, 55)
            end_m_offset = rng.randint(5, 29)  # small offset past noon
            end_h, end_m = 12, (start_m + end_m_offset) % 60
            # If minutes wrapped, it's 12:XX PM with duration < 30 min
            dur_min = (12 * 60 + end_m) - (11 * 60 + start_m)
        else:
            start_h = 23  # 11 PM
            start_m = rng.randint(30, 55)
            end_m_offset = rng.randint(5, 29)
            end_h = 0  # midnight → 12:XX AM if 12h format
            end_m = (start_m + end_m_offset) % 60
            dur_min = (24 * 60 + end_m) - (23 * 60 + start_m)

        start_str = _format_time(start_h, start_m, time_fmt)
        end_str = _format_time(end_h, end_m, time_fmt)
        dur_str = _format_duration(dur_min)

        # Randomly choose question mode: duration or result_time
        question_mode = rng.choice(["duration", "result_time"])

        if question_mode == "duration":
            question = rng.choice(
                _NOON_TRAP_DURATION_TEMPLATES.get(lang, _NOON_TRAP_DURATION_TEMPLATES[Language.EN])
            ).format(start=start_str, end=end_str)
            expected = str(dur_min)
        else:
            question = rng.choice(
                _NOON_TRAP_RESULT_TEMPLATES.get(lang, _NOON_TRAP_RESULT_TEMPLATES[Language.EN])
            ).format(start=start_str, dur=dur_str)
            expected = end_str

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "start_time": start_str,
                "end_time": end_str,
                "duration": dur_str,
                "duration_minutes": dur_min,
                "direction": "forward",
                "expected_answer": expected,
                "is_impossible": False,
                "time_format": time_fmt,
                "question_mode": question_mode,
                "trap_type": "noon" if noon_trap else "midnight",
            },
        )

    # ── day of week ──────────────────────────────────────────────────

    def _gen_day_of_week(self, rng: random.Random, *, sub_type, lang, user_style,
                         sys_style, config_name, direction,
                         max_day_offset, index, seed, **_kw) -> TestCase:
        start_idx = rng.randint(0, 6)
        offset = rng.randint(1, max_day_offset)

        backward = direction == "backward" or (direction == "both" and rng.random() < 0.5)
        if backward:
            result_idx = (start_idx - offset) % 7
        else:
            result_idx = (start_idx + offset) % 7

        day_names = _DAYS_I18N.get(lang, DAYS)
        start_day = day_names[start_idx]
        expected_day = DAYS[result_idx]  # always store English canonical name

        templates = _DAY_OF_WEEK_BACKWARD_TEMPLATES if backward else _DAY_OF_WEEK_TEMPLATES
        question = rng.choice(templates.get(lang, templates[Language.EN])).format(
            day=start_day, n=offset,
        )

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "start_day": start_day,
                "start_day_index": start_idx,
                "offset": offset,
                "direction": "backward" if backward else "forward",
                "expected_answer": expected_day,
                "is_impossible": False,
                "question_mode": "day",
            },
        )

    # ── impossible date ──────────────────────────────────────────────

    def _gen_impossible_date(self, rng: random.Random, *, sub_type, lang,
                             user_style, sys_style, config_name,
                             index, seed, **_kw) -> TestCase:
        month, day = rng.choice(IMPOSSIBLE_DATES)
        year = rng.randint(2000, 2100)

        month_names = _MONTH_NAMES.get(lang, _MONTH_NAMES[Language.EN])
        month_name = month_names.get(month, f"Month {month}")
        date_str = f"{month_name} {day}, {year}"

        question = rng.choice(
            _IMPOSSIBLE_DATE_TEMPLATES.get(lang, _IMPOSSIBLE_DATE_TEMPLATES[Language.EN])
        ).format(date=date_str)

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "month": month,
                "day": day,
                "year": year,
                "date_str": date_str,
                "expected_answer": "impossible",
                "is_impossible": True,
                "question_mode": "date_validity",
            },
        )

    # ── leap year ────────────────────────────────────────────────────

    def _gen_leap_year(self, rng: random.Random, *, sub_type, lang,
                       user_style, sys_style, config_name,
                       year_range, index, seed, **_kw) -> TestCase:
        # Mix curated trap years with random years in range
        if rng.random() < 0.6:
            year, is_leap = rng.choice(LEAP_YEAR_POOL)
        else:
            year = rng.randint(year_range[0], year_range[1])
            is_leap = _is_leap_year(year)

        question = rng.choice(
            _LEAP_YEAR_TEMPLATES.get(lang, _LEAP_YEAR_TEMPLATES[Language.EN])
        ).format(year=year)

        expected = "valid" if is_leap else "impossible"

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "year": year,
                "is_leap": is_leap,
                "expected_answer": expected,
                "is_impossible": not is_leap,
                "question_mode": "date_validity",
            },
        )

    # ── DST trap ─────────────────────────────────────────────────────

    def _gen_dst_trap(self, rng: random.Random, *, sub_type, lang,
                      user_style, sys_style, config_name,
                      index, seed, **_kw) -> TestCase:
        entry = rng.choice(DST_SPRING_FORWARD)
        year, month, day, date_desc = entry
        # Time in the spring-forward hole: 2:00-2:59 AM
        trap_minute = rng.randint(0, 59)
        time_str = f"2:{trap_minute:02d} AM"

        question = rng.choice(
            _DST_TEMPLATES.get(lang, _DST_TEMPLATES[Language.EN])
        ).format(date=date_desc, time=time_str)

        return self._build_test_case(
            lang=lang, user_style=user_style, sys_style=sys_style,
            config_name=config_name, index=index, seed=seed,
            sub_type=sub_type, question=question,
            task_params={
                "sub_type": sub_type,
                "year": year,
                "month": month,
                "day": day,
                "date_desc": date_desc,
                "trap_time": time_str,
                "expected_answer": "impossible",
                "is_impossible": True,
                "question_mode": "date_validity",
            },
        )

    # ── test-case builder ────────────────────────────────────────────

    def _build_test_case(
        self, *, lang: Language, user_style: str,
        sys_style: str, config_name: str, index: int,
        seed: int | None, sub_type: str, question: str,
        task_params: dict[str, Any],
    ) -> TestCase:
        language_str = lang.value
        user_prompt = self._format_user_prompt(
            USER_PROMPT_TEMPLATES, language_str, user_style, question=question,
        )
        system_prompt = self._get_system_prompt(sys_style, language_str)
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

        test_id = f"time_arithmetic_{index:04d}"
        return TestCase(
            test_id=test_id,
            task_type="time_arithmetic",
            config_name=config_name,
            prompts={
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
            },
            task_params=task_params,
            prompt_metadata={
                "user_style": user_style,
                "system_style": sys_style,
                "language": language_str,
            },
            generation_metadata={
                "seed": seed,
                "generator_version": "1.0.0",
                "created_at": datetime.now().isoformat(),
            },
        )
