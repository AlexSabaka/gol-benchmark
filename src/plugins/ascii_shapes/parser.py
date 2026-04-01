"""
ASCII Shapes Response Parser

Multi-strategy parser for extracting answers from model responses.
Supports three answer types: dimensions, counts, and positions.
"""

import re
from typing import Any, Dict, List, Optional, Union

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    re_search_last,
    YES_WORDS, NO_WORDS, merge_keywords, build_answer_label_re, get_language,
)


# ---------------------------------------------------------------------------
# Multilingual dimension keywords
# ---------------------------------------------------------------------------

_DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "en": ["width", "height", "wide", "tall", "high", "across", "columns", "rows"],
    "es": ["ancho", "alto", "columnas", "filas"],
    "fr": ["largeur", "hauteur", "colonnes", "lignes"],
    "de": ["breite", "höhe", "spalten", "zeilen"],
    "zh": ["宽", "高", "列", "行"],
    "ua": ["ширина", "висота", "стовпці", "рядки"],
}


class AsciiShapesResponseParser(ResponseParser):
    """
    Multi-strategy parser for ASCII Shapes model responses.

    Supports three answer types:
    - Dimensions: "WxH", "width: N, height: M", "W by H"
    - Count: numeric answer
    - Position: yes/no/true/false
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response based on question type.

        Args:
            response: Raw model response string
            task_params: Task parameters containing question_type

        Returns:
            ParsedAnswer with appropriate answer type
        """
        lang = get_language(task_params)

        if not response:
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy='failed',
                confidence=0.1,
                error='Empty response from model'
            )

        # Normalize Unicode spaces to regular spaces
        response = re.sub(r'[\u00A0\u202F\u2009\u200B]', ' ', response)
        
        question_type = task_params.get('question_type', 'dimensions')
        response_lower = response.strip().lower()
        response_original = response.strip()

        # Route to appropriate parser
        if question_type == 'dimensions':
            return self._parse_dimensions(response_original, response_lower, lang)
        elif question_type == 'count':
            return self._parse_count(response_original, response_lower, lang)
        elif question_type == 'position':
            return self._parse_position(response_original, response_lower, lang)
        else:
            # Try all parsers
            result = self._parse_dimensions(response_original, response_lower, lang)
            if result.value is not None:
                return result

            result = self._parse_count(response_original, response_lower, lang)
            if result.value is not None:
                return result

            return self._parse_position(response_original, response_lower, lang)

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'dimensions_wxh',
            'dimensions_by',
            'dimensions_keywords',
            'count_keywords',
            'count_number',
            'position_boolean'
        ]

    def _parse_dimensions(self, response: str, response_lower: str, lang: str = "en") -> ParsedAnswer:
        """Parse dimensions answer (WxH format, last match — end-first)."""
        # Build multilingual keyword alternations for width/height patterns
        dim_kws = merge_keywords(_DIMENSION_KEYWORDS, lang)
        w_kws = [k for k in dim_kws if k in (
            "width", "wide", "across", "columns",
            "ancho", "columnas", "largeur", "colonnes",
            "breite", "spalten", "宽", "列", "ширина", "стовпці",
        )]
        h_kws = [k for k in dim_kws if k in (
            "height", "tall", "high", "rows",
            "alto", "filas", "hauteur", "lignes",
            "höhe", "zeilen", "高", "行", "висота", "рядки",
        )]
        w_alt = "|".join(re.escape(k) for k in w_kws) if w_kws else "width|wide|across|columns"
        h_alt = "|".join(re.escape(k) for k in h_kws) if h_kws else "height|tall|high|rows"

        # Strategy 1: direct WxH pattern (highest confidence)
        wxh_patterns = [
            r'(\d+)\s*[x×✕✖]\s*(\d+)',  # "8x5", "8 × 5" (includes Unicode multiplication)
        ]
        for pattern in wxh_patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                try:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    return ParsedAnswer(
                        value=f"{width}x{height}",
                        raw_response=response,
                        parse_strategy='dimensions_wxh',
                        confidence=0.92,
                    )
                except ValueError:
                    continue

        # Strategy 2: "W by H" pattern
        by_pattern = r'(\d+)\s*by\s*(\d+)'
        match = re_search_last(by_pattern, response_lower)
        if match:
            try:
                width = int(match.group(1))
                height = int(match.group(2))
                return ParsedAnswer(
                    value=f"{width}x{height}",
                    raw_response=response,
                    parse_strategy='dimensions_by',
                    confidence=0.88,
                )
            except ValueError:
                pass

        # Strategy 3: keyword-based patterns (multilingual)
        keyword_patterns = [
            rf'(?:{w_alt})\s*[=:]\s*(\d+).*?(?:{h_alt})\s*[=:]\s*(\d+)',
            rf'(\d+)\s*(?:{w_alt}).*?(\d+)\s*(?:{h_alt})',
            rf'(?:{w_alt}).*?(\d+).*?(?:{h_alt}).*?(\d+)',
            # Natural language patterns
            r'(\d+)\s*(?:characters?|symbols?|[a-z]+s?)\s*(?:across|wide).*?(\d+)\s*(?:lines?|rows?|tall|down|high)',
        ]
        for pattern in keyword_patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                try:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    return ParsedAnswer(
                        value=f"{width}x{height}",
                        raw_response=response,
                        parse_strategy='dimensions_keywords',
                        confidence=0.82,
                    )
                except ValueError:
                    continue

        # Fallback: find last two numbers
        all_numbers = re.findall(r'\d+', response)
        if len(all_numbers) == 2:
            try:
                return ParsedAnswer(
                    value=f"{all_numbers[0]}x{all_numbers[1]}",
                    raw_response=response,
                    parse_strategy='dimensions_fallback',
                    confidence=0.70,
                )
            except ValueError:
                pass

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            confidence=0.1,
            error='Could not parse dimensions'
        )

    def _parse_count(self, response: str, response_lower: str, lang: str = "en") -> ParsedAnswer:
        """Parse count answer (numeric, last match — end-first)."""
        # Build multilingual answer-label alternation
        answer_labels = build_answer_label_re(lang)
        count_patterns = [
            rf'(?:{answer_labels}|count|total|number)\s*:?\s*(\d+)',
            r'(?:there are|there\'s|has)\s*(\d+)',
            r'(?:=|equals)\s*(\d+)',
            r'^\s*(\d+)\s*$',  # Just a number alone
        ]

        for pattern in count_patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                try:
                    return ParsedAnswer(
                        value=int(match.group(1)),
                        raw_response=response,
                        parse_strategy='count_keywords',
                        confidence=0.85,
                    )
                except ValueError:
                    continue

        # Fallback: take the last number (end-first)
        all_numbers = re.findall(r'\d+', response)
        if all_numbers:
            try:
                return ParsedAnswer(
                    value=int(all_numbers[-1]),
                    raw_response=response,
                    parse_strategy='count_number',
                    confidence=0.70,
                )
            except ValueError:
                pass

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            confidence=0.1,
            error='Could not parse count'
        )

    def _parse_position(self, response: str, response_lower: str, lang: str = "en") -> ParsedAnswer:
        """Parse position answer (boolean, multilingual)."""
        # Build multilingual yes/no word lists
        yes_words = merge_keywords(YES_WORDS, lang)
        no_words = merge_keywords(NO_WORDS, lang)

        # Extend with domain-specific English words always present
        positive_words = list(dict.fromkeys(yes_words + ['present', 'exists', 'there is']))
        negative_words = list(dict.fromkeys(no_words + ['not present', 'absent', "doesn't exist", 'not', "isn't"]))

        # Check for negation first
        has_negation = any(word in response_lower for word in negative_words)
        has_positive = any(word in response_lower for word in positive_words)

        if has_negation and not has_positive:
            return ParsedAnswer(
                value=False,
                raw_response=response,
                parse_strategy='position_boolean',
                confidence=0.80,
            )

        if has_positive and not has_negation:
            return ParsedAnswer(
                value=True,
                raw_response=response,
                parse_strategy='position_boolean',
                confidence=0.80,
            )

        # Ambiguous — use last occurrence to determine final stance (end-first)
        # Use END position of phrases so "not present" (ending at 69) beats
        # the "present" substring within it (at 62).
        if has_positive and has_negation:
            last_neg_end = max(
                (response_lower.rfind(neg) + len(neg) for neg in negative_words if neg in response_lower),
                default=-1,
            )
            last_pos_end = max(
                (response_lower.rfind(pos) + len(pos) for pos in positive_words if pos in response_lower),
                default=-1,
            )
            # Whichever ends later is the model's final answer
            return ParsedAnswer(
                value=last_pos_end > last_neg_end,
                raw_response=response,
                parse_strategy='position_boolean',
                confidence=0.80,
            )

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            confidence=0.1,
            error='Could not parse position answer'
        )
