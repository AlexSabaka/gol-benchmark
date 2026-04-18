"""Picture Algebra Response Parser.

Extracts a dict ``{variable_token: integer}`` from model responses, with
multilingual support and a sentinel fallback for trick cases
(underdetermined / inconsistent systems).

Strategies, in end-first order:

1. **cannot_be_determined** — dominant refusal phrases, returns a sentinel
2. **boxed_multivar**      — ``\\boxed{x=5, y=7}`` with comma / semicolon / ``\\\\`` splits
3. **label_line**          — per-variable ``<token> = <number>`` (most common)
4. **bold_assignments**    — ``**x = 5**`` markdown-bold assignments
5. **final_answer_block**  — tail after ``answer:`` / ``solution:`` / localized label
6. **coord_tuple**         — ``(5, 7)`` or ``(5, 7, 9)`` positional tuple
7. **last_numbers**        — last *N* integers, positional (weakest)
8. **cannot_be_determined_fallback** — weaker sentinel check after all extractions fail

Each extraction strategy may return a *partial* dict (some vars missing) — the
evaluator grades against ``question_scope`` and the expected-answer key set.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    build_word_to_int,
    get_language,
    last_sentences,
    merge_keywords,
    re_search_last,
    strip_verification_tail,
)

# ── sentinel keywords (multilingual) ────────────────────────────────────

_CANNOT_DETERMINE_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "cannot be determined", "can not be determined",
        "cannot be uniquely determined", "not uniquely determined",
        "underdetermined", "infinitely many solutions",
        "infinite solutions", "infinitely many", "not enough information",
        "insufficient information", "no unique solution",
        "under-determined", "under determined",
    ],
    "es": [
        "no se puede determinar", "no puede determinarse",
        "indeterminado", "infinitas soluciones", "infinitas soluciones",
        "información insuficiente", "sin solución única",
    ],
    "fr": [
        "ne peut pas être déterminé", "ne peut être déterminé",
        "indéterminé", "infinité de solutions", "infiniment de solutions",
        "informations insuffisantes", "pas de solution unique",
    ],
    "de": [
        "nicht bestimmbar", "unterbestimmt",
        "unendlich viele lösungen", "nicht eindeutig bestimmbar",
        "nicht eindeutig", "keine eindeutige lösung",
    ],
    "zh": [
        "无法确定", "不能确定", "欠定", "无穷多解", "无穷多个解", "信息不足",
    ],
    "ua": [
        "не можна визначити", "неможливо визначити",
        "недовизначена", "нескінченно багато розв'язків",
        "недостатньо інформації", "немає єдиного розв'язку",
    ],
}

_NO_SOLUTION_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "no solution", "no valid solution", "inconsistent system",
        "inconsistent", "has no solution", "contradiction",
        "contradictory", "impossible system",
        "over-determined and inconsistent",
    ],
    "es": [
        "no tiene solución", "sin solución", "sistema inconsistente",
        "inconsistente", "contradicción", "contradictorio",
    ],
    "fr": [
        "pas de solution", "sans solution", "système incohérent",
        "incohérent", "contradiction", "contradictoire",
    ],
    "de": [
        "keine lösung", "widersprüchliches system", "widersprüchlich",
        "widerspruch", "inkonsistent",
    ],
    "zh": [
        "没有解", "无解", "方程组不相容", "不相容", "矛盾",
    ],
    "ua": [
        "немає розв'язку", "несумісна система", "несумісна",
        "суперечність", "суперечлива",
    ],
}

# ── numeric parsing helpers ─────────────────────────────────────────────

_SIGNED_INT_RE = re.compile(r"(-?\d+)")


def _try_parse_int(text: str, word_map: Optional[Dict[str, int]] = None) -> Optional[int]:
    """Interpret *text* as a single integer, handling leading +/- and trailing punctuation."""
    s = text.strip().strip("*_`").rstrip(".,;:!?)}]")
    m = re.fullmatch(r"-?\d+", s)
    if m:
        try:
            return int(s)
        except ValueError:
            return None
    if word_map is None:
        return None
    low = s.lower()
    if low in word_map:
        return word_map[low]
    # Try "negative <word>"
    stripped = re.sub(r"^(?:-|negative|minus|\u2212)\s+", "", low)
    if stripped != low and stripped in word_map:
        return -word_map[stripped]
    return None


def _token_alt(tokens: List[str]) -> str:
    """Longest-first alternation over variable tokens."""
    sorted_tokens = sorted(tokens, key=len, reverse=True)
    return "|".join(re.escape(t) for t in sorted_tokens)


# ── parser class ────────────────────────────────────────────────────────

class PictureAlgebraParser(ResponseParser):
    """Multi-variable parser for picture_algebra."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value=None, raw_response=response or "",
                parse_strategy="empty", confidence=0.0,
                error="Empty response",
            )

        raw = str(response).strip()
        tp = task_params or {}
        tokens: List[str] = list(tp.get("variables") or [])
        num_vars = int(tp.get("num_variables", len(tokens) or 2))
        lang = get_language(tp)
        word_map = build_word_to_int(lang)

        if not tokens:
            return ParsedAnswer(
                value=None, raw_response=raw,
                parse_strategy="failed", confidence=0.0,
                error="No variable tokens provided in task_params",
            )

        body = strip_verification_tail(raw)

        # Strategy 1: dominant refusal in the final sentences
        sentinel_strong = self._detect_sentinel(raw, lang, strict=True)
        if sentinel_strong is not None:
            return ParsedAnswer(
                value=sentinel_strong, raw_response=raw,
                parse_strategy="cannot_be_determined", confidence=0.9,
            )

        # Extraction strategies (each returns Optional[Tuple[Dict, strategy_name]])
        for fn in (
            self._strategy_boxed,
            self._strategy_label_line,
            self._strategy_bold_assignments,
            self._strategy_final_answer_block,
        ):
            result = fn(body, tokens, word_map)
            if result is not None:
                values, strat = result
                if values:
                    return ParsedAnswer(
                        value=values, raw_response=raw,
                        parse_strategy=strat,
                        confidence=_confidence_for(values, num_vars, strat),
                    )

        # If the model labelled assignments with foreign keys (e.g.
        # ``a = 5, b = 7`` when our tokens are ``x, y``), surface those
        # as-is so the evaluator can classify ``wrong_variable``.  This must
        # run before positional fallback, which would otherwise convert a
        # wrong-variable answer into a correct-looking positional match.
        foreign = self._strategy_foreign_labels(body, tokens, word_map)
        if foreign is not None:
            return ParsedAnswer(
                value=foreign, raw_response=raw,
                parse_strategy="foreign_labels",
                confidence=0.6,
            )

        # Positional strategies only fire when count matches num_vars
        positional = self._strategy_coord_tuple(body, num_vars, tokens)
        if positional is not None:
            return ParsedAnswer(
                value=positional, raw_response=raw,
                parse_strategy="coord_tuple",
                confidence=0.65,
            )

        positional = self._strategy_last_numbers(body, num_vars, tokens)
        if positional is not None:
            return ParsedAnswer(
                value=positional, raw_response=raw,
                parse_strategy="last_numbers",
                confidence=0.45,
            )

        # Final fallback: weaker sentinel check in full text
        sentinel_weak = self._detect_sentinel(raw, lang, strict=False)
        if sentinel_weak is not None:
            return ParsedAnswer(
                value=sentinel_weak, raw_response=raw,
                parse_strategy="cannot_be_determined_fallback",
                confidence=0.55,
            )

        return ParsedAnswer(
            value=None, raw_response=raw,
            parse_strategy="failed", confidence=0.1,
            error="All parsing strategies failed",
        )

    def get_strategies(self) -> List[str]:
        return [
            "cannot_be_determined",
            "boxed_multivar",
            "label_line",
            "bold_assignments",
            "final_answer_block",
            "foreign_labels",
            "coord_tuple",
            "last_numbers",
            "cannot_be_determined_fallback",
        ]

    # ── sentinel detection ──────────────────────────────────────────

    @staticmethod
    def _detect_sentinel(text: str, lang: str, strict: bool) -> Optional[str]:
        """Return a sentinel string if the model explicitly refused.

        *strict* mode restricts the search to the last three sentences so
        incidental mentions ("this isn't inconsistent with…") don't trigger
        the sentinel.  Non-strict mode scans the whole text as a fallback.
        """
        cannot = [k.lower() for k in merge_keywords(_CANNOT_DETERMINE_KEYWORDS, lang)]
        no_sol = [k.lower() for k in merge_keywords(_NO_SOLUTION_KEYWORDS, lang)]

        haystack_source = "\n".join(last_sentences(text, 3)) if strict else text
        haystack = haystack_source.lower()
        if not haystack:
            return None

        cannot_hit = any(k in haystack for k in cannot)
        no_sol_hit = any(k in haystack for k in no_sol)

        if no_sol_hit:
            return "NO_SOLUTION"
        if cannot_hit:
            return "CANNOT_BE_DETERMINED"
        return None

    # ── extraction strategies ───────────────────────────────────────

    @staticmethod
    def _strategy_boxed(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Tuple[Dict[str, int], str]]:
        """Extract from the last ``\\boxed{...}`` block."""
        m = re_search_last(r"\\boxed\{([^{}]+(?:\{[^{}]*\}[^{}]*)*)\}", text)
        if not m:
            return None
        inner = m.group(1)
        # Split on comma / semicolon / LaTeX double-backslash / newline
        chunks = re.split(r",|;|\\\\|\n|\\,", inner)
        values: Dict[str, int] = {}
        tok_alt = _token_alt(tokens)
        for chunk in chunks:
            pair = re.search(
                rf"({tok_alt})\s*(?:=|≡|:)\s*(-?\d+|\w+)", chunk
            )
            if not pair:
                continue
            token = pair.group(1)
            val = _try_parse_int(pair.group(2), word_map)
            if val is not None:
                values[token] = val
        return (values, "boxed_multivar") if values else None

    @staticmethod
    def _strategy_label_line(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Tuple[Dict[str, int], str]]:
        """For each variable token, find the last ``<token> <sep> <value>`` occurrence.

        Separator is ``=``, ``:``, ``：``, ``equals``, ``is``, or a localized
        verb.  Uses end-first so later assignments override earlier ones
        (e.g. "first try: x=3, actually x=5" → ``x=5``).
        """
        values: Dict[str, int] = {}
        equality_verbs = (
            r"=|==|:|：|≡|"
            r"equals?|is|are|"
            r"vale[n]?|es igual a|es|"  # es
            r"vaut|égale|est\s+égal\s+à|"  # fr
            r"ist|ist\s+gleich|gleich|"  # de
            r"等于|等於|为|為|是|"  # zh
            r"дорівнює|дорівнюють|є"  # ua
        )
        # Two-pass: numeric-first avoids the failure mode where an inner
        # label repeat (``"Solving for y: y = 7"``) greedily consumes the
        # next ``y`` as the captured value.  Word-number fallback runs only
        # when no numeric match is found for a given token.
        numeric_tail = r"(-?\d+)"
        word_tail = r"([^\s,;.!?)]+)"
        for token in tokens:
            token_escaped = re.escape(token)
            numeric_pat = rf"{token_escaped}\s*(?:{equality_verbs})\s*{numeric_tail}"
            last_val: Optional[int] = None
            for m in re.finditer(numeric_pat, text, flags=re.IGNORECASE):
                val = _try_parse_int(m.group(1), word_map)
                if val is not None:
                    last_val = val
            if last_val is None:
                word_pat = rf"{token_escaped}\s*(?:{equality_verbs})\s*{word_tail}"
                for m in re.finditer(word_pat, text, flags=re.IGNORECASE):
                    val = _try_parse_int(m.group(1), word_map)
                    if val is not None:
                        last_val = val
            if last_val is not None:
                values[token] = last_val
        return (values, "label_line") if values else None

    @staticmethod
    def _strategy_bold_assignments(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Tuple[Dict[str, int], str]]:
        """Match ``**<token> = <number>**`` markdown-bold assignments."""
        values: Dict[str, int] = {}
        tok_alt = _token_alt(tokens)
        # Bold block; content may contain multiple assignments comma-separated
        pattern = rf"\*\*([^*]+)\*\*"
        for m in re.finditer(pattern, text):
            inner = m.group(1)
            for chunk in re.split(r",|;|\n", inner):
                pair = re.search(
                    rf"({tok_alt})\s*(?:=|:)\s*(-?\d+|\w+)", chunk
                )
                if not pair:
                    continue
                token = pair.group(1)
                val = _try_parse_int(pair.group(2), word_map)
                if val is not None:
                    values[token] = val  # Later (end-first) overwrites earlier
        return (values, "bold_assignments") if values else None

    @staticmethod
    def _strategy_final_answer_block(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Tuple[Dict[str, int], str]]:
        """Look for ``answer:`` / ``solution:`` / localized label, extract tail."""
        # Using a literal alternation of label keywords keeps multilingual
        # coverage simple and predictable.
        labels = (
            r"final\s+answer|answer|solution|result|"
            r"respuesta|resultado|solución|"
            r"réponse|résultat|solution|"
            r"antwort|ergebnis|lösung|"
            r"答案|解|结果|解答|"
            r"відповідь|результат|рішення|розв'язок"
        )
        m = re_search_last(
            rf"(?:{labels})\s*[:：=]\s*(.*)",
            text, flags=re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return None
        tail = m.group(1)
        values: Dict[str, int] = {}
        tok_alt = _token_alt(tokens)
        # Look for any "token = value" assignments in the tail
        for pair in re.finditer(
            rf"({tok_alt})\s*(?:=|:|equals?|is|vaut|ist|等于|дорівнює)\s*(-?\d+|\w+)",
            tail, flags=re.IGNORECASE,
        ):
            token = pair.group(1)
            val = _try_parse_int(pair.group(2), word_map)
            if val is not None:
                values[token] = val
        return (values, "final_answer_block") if values else None

    @staticmethod
    def _strategy_foreign_labels(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Dict[str, int]]:
        """Detect ``<word> = <integer>`` assignments whose label isn't one of ours.

        Fires when the model answered for *different* variables (e.g. wrote
        ``a = 5, b = 7`` when we asked about ``x, y``).  Preserves the
        model's keys so the evaluator can return ``wrong_variable``.
        """
        # Find plain-label assignments: single alphabetic token (len<=6)
        # followed by ``=`` and an integer.  Emoji tokens are single-char
        # and would match ``\w`` only inconsistently — we intentionally keep
        # this ASCII-letter-only to detect "used letters instead of emoji"
        # cases, which is the realistic wrong-variable failure mode.
        foreign: Dict[str, int] = {}
        ours = {t.lower() for t in tokens}
        for m in re.finditer(
            r"\b([A-Za-z][A-Za-z_0-9]{0,5})\s*=\s*(-?\d+)\b", text,
        ):
            label = m.group(1)
            if label.lower() in ours:
                continue
            try:
                foreign[label] = int(m.group(2))
            except ValueError:
                continue
        if not foreign:
            return None
        # Require at least 2 foreign assignments to distinguish from a stray
        # ``n = 3`` mention in reasoning.
        if len(foreign) < 2:
            return None
        return foreign

    @staticmethod
    def _strategy_coord_tuple(
        text: str, num_vars: int, tokens: List[str],
    ) -> Optional[Dict[str, int]]:
        """Match ``(a, b)`` or ``(a, b, c)`` only when the arity matches."""
        pattern = r"\(\s*(-?\d+)\s*(?:,\s*(-?\d+)\s*){1,2}\)"
        m = re_search_last(pattern, text)
        if not m:
            return None
        nums = re.findall(r"-?\d+", m.group(0))
        if len(nums) != num_vars:
            return None
        try:
            values = [int(n) for n in nums]
        except ValueError:
            return None
        return dict(zip(tokens, values))

    @staticmethod
    def _strategy_last_numbers(
        text: str, num_vars: int, tokens: List[str],
    ) -> Optional[Dict[str, int]]:
        """Weakest fallback: pick the last *num_vars* integers in the text.

        Only fires when exactly *num_vars* integers appear in the last few
        sentences — avoids grabbing intermediate scratch values.
        """
        tail = "\n".join(last_sentences(text, 3))
        if not tail:
            return None
        nums = _SIGNED_INT_RE.findall(tail)
        if len(nums) < num_vars:
            return None
        if len(nums) > num_vars:
            # Prefer the final slice
            nums = nums[-num_vars:]
        try:
            values = [int(n) for n in nums]
        except ValueError:
            return None
        return dict(zip(tokens, values))


# ── confidence helpers ──────────────────────────────────────────────────

def _confidence_for(values: Dict[str, int], num_vars: int, strategy: str) -> float:
    """Base confidence per strategy, reduced proportionally when partial."""
    base = {
        "boxed_multivar": 0.95,
        "label_line": 0.88,
        "bold_assignments": 0.85,
        "final_answer_block": 0.8,
    }.get(strategy, 0.7)
    coverage = len(values) / max(num_vars, 1)
    return round(base * coverage, 3)
