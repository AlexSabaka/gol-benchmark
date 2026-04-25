"""Picture Algebra Response Parser.

Extracts a dict ``{variable_token: number}`` from model responses, with
multilingual support and a sentinel fallback for trick cases
(underdetermined / inconsistent systems).

Strategies, in end-first order:

1. **cannot_be_determined** — dominant refusal phrases, returns a sentinel
2. **boxed_multivar**      — ``\\boxed{x=5, y=7}`` with comma / semicolon / ``\\\\`` splits
3. **label_line**          — per-variable ``<token> = <number>`` (most common)
4. **bold_assignments**    — ``**x = 5**`` markdown-bold assignments
5. **final_answer_block**  — tail after ``answer:`` / ``solution:`` / localized label
6. **foreign_labels** / **foreign_labels_aliased** — model used different keys;
   if an alias (``Let x = 🍎``) was declared, remap back to the expected token
7. **coord_tuple**         — ``(5, 7)`` or ``(5, 7, 9)`` positional tuple
8. **last_numbers**        — last *N* integers, positional (weakest)
9. **cannot_be_determined_fallback** — weaker sentinel check after all extractions fail

Round 1 annotation-driven changes (v2.25.1):

- ``strip_verification_tail`` is **no longer called** — models verify during
  reasoning (``"(This matches…)"``) and then print the final answer; stripping
  decapitates the response.
- Each extraction strategy runs on text normalized by
  ``_normalize_for_label_matching`` — LaTeX wrappers (``\\text{…}``, ``$…$``,
  ``\\quad``) are replaced so ``<token>\\s*=\\s*<num>`` patterns reach across
  math-mode markup.
- Separator patterns tolerate markdown delimiters (``*+`` / ``_+``) between the
  token and the equality sign: ``**🦆** = 4`` now parses.
- ``foreign_labels`` is **guarded** — it only fires when NO ``<emoji>=<num>``
  pattern exists anywhere in the normalized text.  Prevents the strategy from
  shipping reasoning intermediates (``x = 11, y = 4``) when the model actually
  concluded with emoji assignments.
- Alias remap: when ``foreign_labels`` fires but the model declared aliases
  (``Let x = 🍎``), remap the foreign keys back to the expected emoji tokens
  and emit as ``foreign_labels_aliased`` — the evaluator scores these as
  ``correct`` because the math matches.
- Non-integer predictions (``22.2``, ``7.5``) are now captured as floats so
  the evaluator can flag ``non_integer_prediction`` in details.

Each extraction strategy may return a *partial* dict (some vars missing) — the
evaluator grades against ``question_scope`` and the expected-answer key set.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    Number,
    build_answer_label_re,
    build_word_to_int,
    get_language,
    last_sentences,
    merge_keywords,
    normalize_for_label_matching,
    normalize_unicode,
    re_search_last,
    try_parse_number,
)

# Picture-algebra-specific labels layered on top of ANSWER_LABELS.
# `conclusion` / `розв'язок` are common in algebra-style answers; the base
# ANSWER_LABELS dict covers answer / result / final answer / solution.
_EXTRA_LABELS: Dict[str, List[str]] = {
    "en": ["conclusion"],
    "es": ["conclusión"],
    "fr": ["conclusion"],
    "de": ["schlussfolgerung"],
    "zh": ["结论"],
    "ua": ["висновок", "розв'язок"],
}


def _build_label_alt(lang: str) -> str:
    base = build_answer_label_re(lang)
    extra = merge_keywords(_EXTRA_LABELS, lang)
    extra_alt = "|".join(re.escape(e) for e in extra) if extra else ""
    if base and extra_alt:
        return f"{base}|{extra_alt}"
    return base or extra_alt

# ── sentinel keywords (multilingual) ────────────────────────────────────

_CANNOT_DETERMINE_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "cannot be determined", "can not be determined",
        "cannot be uniquely determined", "not uniquely determined",
        "underdetermined", "infinitely many solutions",
        "infinite solutions", "infinitely many", "not enough information",
        "insufficient information", "no unique solution",
        "no unique answer", "no unique integer solution",
        "not have a unique solution", "not have a unique answer",
        "doesn't have a unique answer", "does not have a unique",
        "under-determined", "under determined",
    ],
    "es": [
        "no se puede determinar", "no puede determinarse",
        "indeterminado", "infinitas soluciones",
        "información insuficiente", "sin solución única",
        # — gemma3 / gpt-5.4-mini observed forms —
        "no tiene una única solución", "no tiene solución única",
        "no tiene una única", "no es única", "no única",
        "podría no tener una solución única", "no podemos determinar",
        "múltiples valores", "valores múltiples", "pueden tomar",
        "infinitas posibilidades",
    ],
    "fr": [
        "ne peut pas être déterminé", "ne peut être déterminé",
        "indéterminé", "infinité de solutions", "infiniment de solutions",
        "informations insuffisantes", "pas de solution unique",
        # — observed forms —
        "n'a pas de solution unique", "n’a pas de solution unique",
        "pas une solution unique", "aucune solution unique",
    ],
    "de": [
        "nicht bestimmbar", "unterbestimmt",
        "unendlich viele lösungen", "nicht eindeutig bestimmbar",
        "nicht eindeutig", "keine eindeutige lösung",
        # — observed forms —
        "keine eindeutige ganzzahlige lösung",
        "hat keine eindeutige", "ohne eindeutige lösung",
    ],
    "zh": [
        "无法确定", "不能确定", "欠定", "无穷多解", "无穷多个解",
        "信息不足", "无穷多",
        # — observed forms —
        "没有唯一解", "没有唯一的解", "解不唯一",
        "不能唯一确定", "无法唯一确定", "唯一确定不了",
        "没有唯一的整数解", "没有唯一整数解",
        "没有整数解", "方程组没有整数解",
    ],
    "ua": [
        "не можна визначити", "неможливо визначити",
        "недовизначена", "нескінченно багато розв'язків",
        "недостатньо інформації",
        # — observed forms — apostrophes normalized to U+0027 ' before match
        "не має єдиного розв'язку", "немає єдиного розв'язку",
        "не має єдиного цілочисельного розв'язку",
        "не має єдиного", "єдиного розв'язку немає",
        "єдиного набору значень немає",
        "безліч розв'язків", "безліч цілих розв'язків",
        "безліч цілочисельних розв'язків",
        # Common typo seen in model output ("безлічниих") — keep as-is.
        "безлічниих",
        "багато розв'язків", "нескінченно багато",
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
        # — observed forms —
        "no tiene una solución", "sin solución entera",
        "no admite solución", "sistema incompatible",
    ],
    "fr": [
        "pas de solution", "sans solution", "système incohérent",
        "incohérent", "contradiction", "contradictoire",
        # — observed forms —
        "n'a pas de solution", "n’a pas de solution",
        "système incompatible", "incompatible",
    ],
    "de": [
        "keine lösung", "widersprüchliches system", "widersprüchlich",
        "widerspruch", "inkonsistent",
        # — observed forms —
        "keine ganzzahlige lösung", "hat keine lösung",
    ],
    "zh": [
        "没有解", "无解", "方程组不相容", "不相容", "矛盾",
        # — observed forms —
        "方程组无解", "方程组没有解",
    ],
    "ua": [
        "немає розв'язку", "несумісна система", "несумісна",
        "суперечність", "суперечлива",
        # — observed forms — apostrophes normalized to U+0027 ' before match
        "не має розв'язку", "система не має розв'язку",
        "система рівнянь не має розв'язку",
        "система несумісна", "несумісні рівняння",
    ],
}

# ── markdown wrap tolerance ──────────────────────────────────────────────

# Optional ``*+`` / ``_+`` between two tokens — handles ``**🦆** = 4``,
# ``*🦆* = 4``, ``_🦆_ = 4``, and value-side wraps like ``= **4**``.
_MD_WRAP = r"(?:\s*[*_]+)?"


# ── local numeric regex (used only for bare-digit scans, not full parsing) ──

_SIGNED_INT_RE = re.compile(r"(-?\d+)")


def _token_alt(tokens: List[str]) -> str:
    """Longest-first alternation over variable tokens."""
    sorted_tokens = sorted(tokens, key=len, reverse=True)
    return "|".join(re.escape(t) for t in sorted_tokens)


# ── guard: any emoji assignment in text ──────────────────────────────────

def _text_contains_token_assignment(text: str, tokens: List[str]) -> bool:
    """True if any ``<token>\\s*=\\s*<number>`` exists anywhere in *text*.

    Used as a guard before falling through to ``foreign_labels``: when the
    model *did* state emoji assignments somewhere, shipping reasoning
    intermediates would be strictly worse than whatever partial extraction
    the earlier strategies produced.
    """
    for token in tokens:
        pat = (
            rf"{re.escape(token)}\s*{_MD_WRAP}\s*"
            r"(?:=|:)\s*"
            rf"{_MD_WRAP}\s*-?\d+(?:\.\d+)?"
        )
        if re.search(pat, text):
            return True
    return False


# ── alias detection ──────────────────────────────────────────────────────

def _detect_aliases(text: str, tokens: List[str]) -> Dict[str, str]:
    """Return ``{letter: emoji}`` for ``let x = 🍎``-style aliasing.

    Handles the common phrasings LLMs use when solving emoji algebra by
    substituting a Latin letter, solving for the letter, and then failing
    to restate values against the emoji.  Round-1 scope: EN-only,
    single-character Latin letters, emoji/nonsense tokens on the other side.
    """
    if not tokens:
        return {}
    tok_alt = _token_alt(tokens)
    aliases: Dict[str, str] = {}

    # letter-first forms — group 1 is the letter, group 2 is the token
    letter_first = [
        # "Let x = 🍎" / "let x be 🍎" / "let x represent the value of 🍎"
        rf"\blet\s+([a-zA-Z])\s+(?:be|=|represents?|denotes?|stands?\s+for)"
        rf"\s+(?:the\s+(?:value|symbol)\s+(?:of\s+)?(?:the\s+symbol\s+)?)?"
        rf"(?:[*_]+\s*)?({tok_alt})",
        # "x = 🍎" (bare — safe because group 2 must be an emoji token, so
        # ``x = 5`` reasoning can't false-match)
        rf"\b([a-zA-Z])\s*=\s*(?:[*_]+)?\s*({tok_alt})",
        # "x for 🍎" / "x stands for 🍎" / "x represents 🍎"
        rf"\b([a-zA-Z])\s+(?:for|stands?\s+for|represents?|denotes?)"
        rf"\s+(?:the\s+(?:value|symbol)\s+(?:of\s+)?)?"
        rf"(?:[*_]+)?\s*({tok_alt})",
    ]

    # token-first forms — group 1 is the token, group 2 is the letter
    token_first = [
        # "🍎 = x"
        rf"({tok_alt})\s*=\s*(?:[*_]+)?\s*([a-zA-Z])\b",
        # "🍎 is x" / "🍎 represents x"
        rf"({tok_alt})\s+(?:is|represents?|denotes?)\s+"
        rf"(?:the\s+variable\s+)?([a-zA-Z])\b",
    ]

    for pat in letter_first:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            letter, emoji = m.group(1).lower(), m.group(2)
            if len(letter) == 1 and letter.isalpha() and emoji in tokens:
                aliases.setdefault(letter, emoji)

    for pat in token_first:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            emoji, letter = m.group(1), m.group(2).lower()
            if len(letter) == 1 and letter.isalpha() and emoji in tokens:
                aliases.setdefault(letter, emoji)

    return aliases


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

        raw = normalize_unicode(str(response).strip())
        tp = task_params or {}
        tokens: List[str] = list(tp.get("variables") or [])
        num_vars = int(tp.get("num_variables", len(tokens) or 2))
        lang = get_language(tp)
        word_map = build_word_to_int(lang)
        question_scope = tp.get("question_scope")
        queried_variable = tp.get("queried_variable")

        if not tokens:
            return ParsedAnswer(
                value=None, raw_response=raw,
                parse_strategy="fallback", confidence=0.0,
                error="No variable tokens provided in task_params",
            )

        # Sentinel detection runs on the raw text so refusal phrasing is
        # not mangled by LaTeX normalization.
        sentinel_strong = self._detect_sentinel(raw, lang, strict=True)
        if sentinel_strong is not None:
            return ParsedAnswer(
                value=sentinel_strong, raw_response=raw,
                parse_strategy="cannot_be_determined", confidence=0.9,
            )

        # All extraction strategies run on normalized text so LaTeX
        # wrappers don't block token-adjacent pattern matching.
        normalized = normalize_for_label_matching(raw)

        # Boxed strategy gets question_scope/queried_variable for the
        # boxed_single_value path (``\\boxed{11}``).
        boxed_result = self._strategy_boxed(
            normalized, tokens, word_map,
            question_scope=question_scope,
            queried_variable=queried_variable,
        )
        if boxed_result is not None:
            values, strat = boxed_result
            if values:
                return ParsedAnswer(
                    value=values, raw_response=raw,
                    parse_strategy=strat,
                    confidence=_confidence_for(values, num_vars, strat),
                )

        for fn in (
            self._strategy_label_line,
            self._strategy_bold_assignments,
            # final_answer_block takes lang for the multilingual label
            # alternation; wrap it so the loop-invoked signature stays uniform.
            lambda t, tk, wm: self._strategy_final_answer_block(t, tk, wm, lang),
        ):
            result = fn(normalized, tokens, word_map)
            if result is not None:
                values, strat = result
                if values:
                    return ParsedAnswer(
                        value=values, raw_response=raw,
                        parse_strategy=strat,
                        confidence=_confidence_for(values, num_vars, strat),
                    )

        # Foreign-labels guard: if the model DID write emoji assignments
        # anywhere in the response, don't ship the reasoning's x/y
        # intermediates instead.  Earlier strategies missed for some other
        # reason (unusual formatting); positional fallback is less wrong.
        if not _text_contains_token_assignment(normalized, tokens):
            foreign = self._strategy_foreign_labels(normalized, tokens, word_map)
            if foreign is not None:
                # Alias remap — if "Let x = 🍎" was declared, convert foreign
                # letter keys back to the expected emoji tokens.  Partial
                # maps (only some letters aliased) remap only what's
                # declared; unaliased keys stay as-is so the evaluator can
                # still classify the unaliased half as wrong_variable.
                aliases = _detect_aliases(normalized, tokens)
                remapped: Dict[str, Number] = {}
                remap_applied = False
                for key, value in foreign.items():
                    mapped = aliases.get(key.lower())
                    if mapped is not None:
                        remapped[mapped] = value
                        remap_applied = True
                    else:
                        remapped[key] = value
                if remap_applied:
                    return ParsedAnswer(
                        value=remapped, raw_response=raw,
                        parse_strategy="foreign_labels_aliased",
                        confidence=0.75,
                    )
                return ParsedAnswer(
                    value=foreign, raw_response=raw,
                    parse_strategy="foreign_labels",
                    confidence=0.6,
                )

        # Positional strategies only fire when count matches num_vars
        positional = self._strategy_coord_tuple(normalized, num_vars, tokens)
        if positional is not None:
            return ParsedAnswer(
                value=positional, raw_response=raw,
                parse_strategy="coord_tuple",
                confidence=0.65,
            )

        positional = self._strategy_last_numbers(normalized, num_vars, tokens)
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
            parse_strategy="fallback", confidence=0.1,
            error="All parsing strategies failed",
        )

    def get_strategies(self) -> List[str]:
        return [
            "cannot_be_determined",
            "boxed_multivar",
            "boxed_single_value",
            "label_line",
            "bold_assignments",
            "final_answer_block",
            "foreign_labels",
            "foreign_labels_aliased",
            "coord_tuple",
            "last_numbers",
            "cannot_be_determined_fallback",
        ]

    # ── sentinel detection ──────────────────────────────────────────

    @staticmethod
    def _detect_sentinel(text: str, lang: str, strict: bool) -> Optional[str]:
        """Return a sentinel string if the model explicitly refused.

        *strict* mode restricts the search to the **first 2 + last 3**
        sentences so incidental mid-reasoning mentions ("this isn't
        inconsistent with…") don't trigger the sentinel — but
        leading-with-conclusion responses ("Das System hat keine eindeutige
        Lösung. Hier ist warum…") are still caught.

        Sentence-splitting also recognizes Chinese punctuation (。！？),
        and U+2019 (curly apostrophe) is normalized to U+0027 (straight)
        so Ukrainian responses match regardless of which apostrophe glyph
        the model emits.
        """
        cannot = [k.lower().replace("\u2019", "'") for k in merge_keywords(_CANNOT_DETERMINE_KEYWORDS, lang)]
        no_sol = [k.lower().replace("\u2019", "'") for k in merge_keywords(_NO_SOLUTION_KEYWORDS, lang)]

        if strict:
            # Inline split — the shared `last_sentences` only handles ASCII
            # punctuation, leaving Chinese text as one mega-sentence.
            sentences = re.split(r"(?<=[.!?。！？])\s+", text.strip())
            sentences = [s for s in sentences if s.strip()]
            if not sentences:
                return None
            head = sentences[:2]
            tail = sentences[-3:]
            # Dedupe (head and tail can overlap on short responses)
            relevant: List[str] = []
            seen_ids: set = set()
            for s in head + tail:
                if id(s) not in seen_ids:
                    seen_ids.add(id(s))
                    relevant.append(s)
            haystack_source = "\n".join(relevant)
        else:
            haystack_source = text

        haystack = haystack_source.lower().replace("\u2019", "'")
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
        *,
        question_scope: Optional[str] = None,
        queried_variable: Optional[str] = None,
    ) -> Optional[Tuple[Dict[str, Number], str]]:
        """Extract from the last ``\\boxed{...}`` block.

        Two paths:

        1. **boxed_multivar** — inner contains ``<token>=<num>`` pairs
        2. **boxed_single_value** — inner is just a number; assign it to the
           queried variable (when ``question_scope='specific'``) or to the
           nearest emoji token preceding the boxed block (within 200 chars).
        """
        m = re_search_last(r"\\boxed\{([^{}]+(?:\{[^{}]*\}[^{}]*)*)\}", text)
        if not m:
            return None
        inner = m.group(1)
        # ── Path 1: boxed_multivar (existing) ──
        chunks = re.split(r",|;|\\\\|\n|\\,", inner)
        values: Dict[str, Number] = {}
        tok_alt = _token_alt(tokens)
        for chunk in chunks:
            pair = re.search(
                rf"({tok_alt})\s*{_MD_WRAP}\s*(?:=|≡|:)\s*{_MD_WRAP}\s*"
                r"(-?\d+(?:\.\d+)?|\w+)",
                chunk,
            )
            if not pair:
                continue
            token = pair.group(1)
            val = try_parse_number(pair.group(2), word_map)
            if val is not None:
                values[token] = val
        if values:
            return (values, "boxed_multivar")

        # ── Path 2: boxed_single_value ──
        bare = inner.strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", bare):
            num = try_parse_number(bare, word_map)
            if num is None:
                return None
            # 2a. Specific scope → assign to queried variable
            if question_scope == "specific" and queried_variable in tokens:
                return ({queried_variable: num}, "boxed_single_value")
            # 2b. Otherwise → look back ≤200 chars for the nearest token
            window_start = max(0, m.start() - 200)
            window = text[window_start:m.start()]
            preceding = re_search_last(rf"({tok_alt})", window)
            if preceding:
                token = preceding.group(1)
                return ({token: num}, "boxed_single_value")
        return None

    @staticmethod
    def _strategy_label_line(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Tuple[Dict[str, Number], str]]:
        """For each variable token, find the last ``<token> <sep> <value>`` occurrence.

        Separator is ``=``, ``:``, ``：``, ``equals``, ``is``, or a localized
        verb.  Tolerates surrounding markdown delimiters (``**``, ``*``,
        ``_``).  Uses end-first so later assignments override earlier ones.
        """
        values: Dict[str, Number] = {}
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
        numeric_tail = r"(-?\d+(?:\.\d+)?)"
        word_tail = r"([^\s,;.!?)]+)"
        for token in tokens:
            token_escaped = re.escape(token)
            numeric_pat = (
                rf"{token_escaped}\s*{_MD_WRAP}\s*"
                rf"(?:{equality_verbs})\s*"
                rf"{_MD_WRAP}\s*{numeric_tail}"
            )
            last_val: Optional[Number] = None
            for m in re.finditer(numeric_pat, text, flags=re.IGNORECASE):
                val = try_parse_number(m.group(1), word_map)
                if val is not None:
                    last_val = val
            if last_val is None:
                word_pat = (
                    rf"{token_escaped}\s*{_MD_WRAP}\s*"
                    rf"(?:{equality_verbs})\s*"
                    rf"{_MD_WRAP}\s*{word_tail}"
                )
                for m in re.finditer(word_pat, text, flags=re.IGNORECASE):
                    val = try_parse_number(m.group(1), word_map)
                    if val is not None:
                        last_val = val
            if last_val is not None:
                values[token] = last_val
        return (values, "label_line") if values else None

    @staticmethod
    def _strategy_bold_assignments(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Tuple[Dict[str, Number], str]]:
        """Match ``**<token> = <number>**`` markdown-bold assignments."""
        values: Dict[str, Number] = {}
        tok_alt = _token_alt(tokens)
        pattern = r"\*\*([^*]+)\*\*"
        for m in re.finditer(pattern, text):
            inner = m.group(1)
            for chunk in re.split(r",|;|\n", inner):
                pair = re.search(
                    rf"({tok_alt})\s*{_MD_WRAP}\s*(?:=|:)\s*{_MD_WRAP}\s*"
                    r"(-?\d+(?:\.\d+)?|\w+)",
                    chunk,
                )
                if not pair:
                    continue
                token = pair.group(1)
                val = try_parse_number(pair.group(2), word_map)
                if val is not None:
                    values[token] = val  # Later (end-first) overwrites earlier
        return (values, "bold_assignments") if values else None

    @staticmethod
    def _strategy_final_answer_block(
        text: str, tokens: List[str], word_map: Dict[str, int], lang: str = "en",
    ) -> Optional[Tuple[Dict[str, Number], str]]:
        """Look for ``answer:`` / ``solution:`` / localized label, extract tail.

        Uses the shared multilingual `build_answer_label_re` plus picture
        -algebra-specific extras (``conclusion`` / ``розв'язок``) so the
        supported label set stays in sync with the rest of the benchmark.
        """
        labels = _build_label_alt(lang)
        m = re_search_last(
            rf"(?:{labels})\s*[:：=]?\s*(.*)",
            text, flags=re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return None
        tail = m.group(1)
        values: Dict[str, Number] = {}
        tok_alt = _token_alt(tokens)
        for pair in re.finditer(
            rf"({tok_alt})\s*{_MD_WRAP}\s*"
            r"(?:=|:|equals?|is|vaut|ist|等于|дорівнює)\s*"
            rf"{_MD_WRAP}\s*(-?\d+(?:\.\d+)?|\w+)",
            tail, flags=re.IGNORECASE,
        ):
            token = pair.group(1)
            val = try_parse_number(pair.group(2), word_map)
            if val is not None:
                values[token] = val
        return (values, "final_answer_block") if values else None

    @staticmethod
    def _strategy_foreign_labels(
        text: str, tokens: List[str], word_map: Dict[str, int],
    ) -> Optional[Dict[str, Number]]:
        """Detect ``<word> = <integer>`` assignments whose label isn't one of ours.

        Fires when the model answered for *different* variables (e.g. wrote
        ``a = 5, b = 7`` when we asked about ``x, y``).  Preserves the
        model's keys so the evaluator can return ``wrong_variable``, or so
        alias remap can convert the keys back to emoji tokens.
        """
        foreign: Dict[str, Number] = {}
        ours = {t.lower() for t in tokens}
        pattern = (
            r"\b([A-Za-z][A-Za-z_0-9]{0,5})\s*"
            + _MD_WRAP
            + r"\s*=\s*"
            + _MD_WRAP
            + r"\s*(-?\d+(?:\.\d+)?)\b"
        )
        for m in re.finditer(pattern, text):
            label = m.group(1)
            if label.lower() in ours:
                continue
            val = try_parse_number(m.group(2))
            if val is None:
                continue
            foreign[label] = val
        if len(foreign) < 2:
            # Require at least 2 assignments to distinguish from a stray
            # ``n = 3`` mention in reasoning.
            return None
        return foreign

    @staticmethod
    def _strategy_coord_tuple(
        text: str, num_vars: int, tokens: List[str],
    ) -> Optional[Dict[str, Number]]:
        """Match ``(a, b)`` or ``(a, b, c)`` only when the arity matches."""
        pattern = r"\(\s*(-?\d+(?:\.\d+)?)\s*(?:,\s*(-?\d+(?:\.\d+)?)\s*){1,2}\)"
        m = re_search_last(pattern, text)
        if not m:
            return None
        nums = re.findall(r"-?\d+(?:\.\d+)?", m.group(0))
        if len(nums) != num_vars:
            return None
        values: List[Number] = []
        for n in nums:
            parsed = try_parse_number(n)
            if parsed is None:
                return None
            values.append(parsed)
        return dict(zip(tokens, values))

    @staticmethod
    def _strategy_last_numbers(
        text: str, num_vars: int, tokens: List[str],
    ) -> Optional[Dict[str, Number]]:
        """Weakest fallback: pick the last *num_vars* integers in the text."""
        tail = "\n".join(last_sentences(text, 3))
        if not tail:
            return None
        nums = _SIGNED_INT_RE.findall(tail)
        if len(nums) < num_vars:
            return None
        if len(nums) > num_vars:
            nums = nums[-num_vars:]
        try:
            values = [int(n) for n in nums]
        except ValueError:
            return None
        return dict(zip(tokens, values))


# ── confidence helpers ──────────────────────────────────────────────────

def _confidence_for(values: Dict[str, Number], num_vars: int, strategy: str) -> float:
    """Base confidence per strategy, reduced proportionally when partial."""
    base = {
        "boxed_multivar": 0.95,
        "boxed_single_value": 0.85,
        "label_line": 0.88,
        "bold_assignments": 0.85,
        "final_answer_block": 0.8,
    }.get(strategy, 0.7)
    coverage = len(values) / max(num_vars, 1)
    return round(base * coverage, 3)
