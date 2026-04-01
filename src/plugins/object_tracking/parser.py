"""
Object Tracking Response Parser

Multi-strategy parser for extracting location answers from LLM responses.
Handles various response formats from single words to full sentences.
"""

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import (
    re_search_last, strip_verification_tail,
    merge_keywords, build_answer_label_re, get_language,
)


# ---------------------------------------------------------------------------
# Multilingual stop words  (always merged with English at runtime)
# ---------------------------------------------------------------------------

_STOP_WORDS: Dict[str, set] = {
    "en": {'the', 'a', 'an', 'on', 'in', 'at', 'to', 'of', 'for', 'is', 'be', 'was', 'were',
           'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
           'should', 'must', 'i', 'you', 'he', 'she', 'they', 'we', 'my', 'your',
           'answer', 'location', 'place', 'position', 'where',
           'now', 'currently', 'still', 'therefore', 'thus',
           'yes', 'no', 'not', 'likely', 'probably', 'maybe'},
    "es": {'el', 'la', 'los', 'las', 'un', 'una', 'en', 'de', 'por', 'es', 'está', 'fue',
           'ser', 'haber', 'respuesta', 'ubicación', 'lugar', 'posición', 'dónde',
           'ahora', 'actualmente', 'todavía', 'sí', 'no'},
    "fr": {'le', 'la', 'les', 'un', 'une', 'dans', 'sur', 'de', 'pour', 'est', 'était',
           'être', 'avoir', 'réponse', 'emplacement', 'lieu', 'position', 'où',
           'maintenant', 'actuellement', 'encore', 'oui', 'non'},
    "de": {'der', 'die', 'das', 'ein', 'eine', 'auf', 'in', 'an', 'zu', 'von', 'für',
           'ist', 'war', 'sein', 'haben', 'antwort', 'ort', 'stelle', 'position', 'wo',
           'jetzt', 'derzeit', 'noch', 'ja', 'nein'},
    "zh": {'的', '在', '了', '是', '有', '这', '那', '个', '和', '与',
           '答案', '位置', '地方', '现在', '目前', '是的', '不'},
    "ua": {'в', 'у', 'на', 'до', 'з', 'за', 'є', 'був', 'була', 'бути', 'мати',
           'відповідь', 'місце', 'розташування', 'позиція', 'де',
           'зараз', 'наразі', 'все ще', 'так', 'ні'},
}

# ---------------------------------------------------------------------------
# Multilingual location verbs  (merged with English when building patterns)
# ---------------------------------------------------------------------------

_LOCATION_VERBS: Dict[str, str] = {
    "en": r"is|remains|stayed|fell|dropped|ended up|landed|rests|sitting|located|found|resting",
    "es": r"está|permanece|quedó|cayó|se encuentra|ubicado|encontrado",
    "fr": r"est|reste|resté|tombé|se trouve|situé|trouvé",
    "de": r"ist|bleibt|blieb|fiel|befindet sich|liegt|gefunden",
    "zh": r"在|留在|掉在|位于|放在|落在",
    "ua": r"є|залишається|залишився|впав|знаходиться|розташований",
}


class ObjectTrackingResponseParser(ResponseParser):
    """
    Multi-strategy parser for object tracking responses.

    Parsing Strategies (in order of preference):
    1. single_word - Response is a single word
    2. answer_prefix - "Answer: location" or "The answer is: location"
    3. sentence_pattern - "The {object} is on/in the {location}"
    4. location_keyword - Find known location word in response
    5. last_word - Extract last meaningful word
    """

    def __init__(self):
        # Location synonyms for normalization (English — scenario locations
        # are always English words like "counter", "table", "shelf")
        self.location_synonyms = {
            # Counter variations
            'countertop': 'counter',
            'kitchen counter': 'counter',
            'work surface': 'counter',
            'worktop': 'counter',
            'benchtop': 'counter',

            # Table variations
            'tabletop': 'table',
            'dining table': 'table',
            'kitchen table': 'table',
            'coffee table': 'table',

            # Shelf variations
            'bookshelf': 'shelf',
            'shelving': 'shelf',
            'cupboard shelf': 'shelf',

            # Floor variations
            'ground': 'floor',
            'flooring': 'floor',

            # Desk variations
            'desktop': 'desk',
            'writing desk': 'desk',
            'work desk': 'desk',
        }

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse model response to extract location answer.

        Args:
            response: Raw model response
            task_params: Task parameters including known locations

        Returns:
            ParsedAnswer with extracted location or error
        """
        if not response:
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy='failed',
                error='Empty response'
            )

        lang = get_language(task_params)
        stop_words = _STOP_WORDS["en"] | _STOP_WORDS.get(lang, set())

        response = response.strip()
        known_locations = self._get_known_locations(task_params)
        obj = task_params.get('object', 'object')

        # Strip verification/confirmation tails for pattern-based strategies
        # so we don't grab locations from re-computation sections
        cleaned = strip_verification_tail(response)

        # Try each strategy in order
        strategies = [
            ('single_word', lambda: self._strategy_single_word(response, stop_words)),
            ('answer_prefix', lambda: self._strategy_answer_prefix(response, lang, stop_words)),
            ('bold_keyword', lambda: self._strategy_bold_keyword(response, known_locations)),
            ('first_sentence_location', lambda: self._strategy_first_sentence_location(cleaned, known_locations)),
            ('sentence_pattern', lambda: self._strategy_sentence_pattern(cleaned, obj, lang, stop_words)),
            ('location_keyword', lambda: self._strategy_location_keyword(cleaned, known_locations)),
            ('last_word', lambda: self._strategy_last_word(cleaned, stop_words)),
        ]

        for name, strategy_func in strategies:
            try:
                result = strategy_func()
                if result:
                    normalized = self._normalize_location(result)
                    confidence = 1.0 if name in ['single_word', 'answer_prefix'] else 0.8
                    return ParsedAnswer(
                        value=normalized,
                        raw_response=response,
                        parse_strategy=name,
                        confidence=confidence
                    )
            except Exception:
                continue

        # All strategies failed
        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            error='All parsing strategies failed'
        )

    def _strategy_single_word(self, response: str, stop_words: set) -> Optional[str]:
        """
        Extract answer if response is a single word.

        Handles responses like:
        - "counter"
        - "Counter."
        - "counter!"
        """
        # Clean response and split
        clean = re.sub(r'[^\w\s]', '', response).strip()
        words = clean.lower().split()

        # Filter out stop words
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 1]

        if len(meaningful_words) == 1:
            return meaningful_words[0]

        # Also accept if original response was a single "word" with punctuation
        if len(words) == 1:
            return words[0]

        return None

    def _strategy_answer_prefix(self, response: str, lang: str, stop_words: set) -> Optional[str]:
        """
        Look for "Answer: X" or similar patterns (last match — end-first).

        Handles responses like:
        - "Answer: counter"
        - "The answer is counter"
        - "Location: table"
        - "It's on the counter"

        Uses ``build_answer_label_re`` for multilingual label matching.
        """
        answer_labels = build_answer_label_re(lang)
        patterns = [
            rf'(?:{answer_labels}|location|place)[:\s]+(\w+)',
            rf'the (?:{answer_labels}) is[:\s]+(\w+)',
            r'(?:it\'s|it is|that\'s|that is) (?:on|in|at) (?:the )?(\w+)',
            r'(?:still|now|currently) (?:on|in|at) (?:the )?(\w+)',
            r'^(?:on|in|at) (?:the )?(\w+)',  # Starts with preposition
        ]

        response_lower = response.lower()
        for pattern in patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                word = match.group(1)
                if word not in stop_words:
                    return word

        return None

    def _strategy_bold_keyword(
        self,
        response: str,
        known_locations: List[str],
    ) -> Optional[str]:
        """
        Extract the FIRST bold text that matches a known location.

        Models consistently bold the answer: "The keys are on the **counter**."
        Later bolds in the explanation are distractors, so we use the FIRST
        match (not last) — an intentional exception to the end-first convention.
        """
        for m in re.finditer(r"\*\*([^*]{1,40})\*\*", response):
            bold_text = m.group(1).lower().strip()
            # Check if the bold text is or contains a known location
            for loc in known_locations:
                if loc.lower() in bold_text:
                    return loc
            # Also check synonyms
            normalized = self._normalize_location(bold_text)
            if normalized != bold_text:
                for loc in known_locations:
                    if loc.lower() == normalized:
                        return loc
        return None

    def _strategy_first_sentence_location(
        self,
        response: str,
        known_locations: List[str],
    ) -> Optional[str]:
        """
        Extract a known location from the first sentence.

        Models typically state the answer upfront: "The marble is on the table."
        We limit the search to the first sentence to avoid distractor locations
        in explanations that follow.
        """
        # Get first sentence (up to first period or double newline)
        first_sent_match = re.match(r"([^\n.]+[.]?)", response)
        if not first_sent_match:
            return None

        first_sent = first_sent_match.group(1).lower()

        # Check known locations — prefer longer matches first
        sorted_locations = sorted(known_locations, key=len, reverse=True)
        for loc in sorted_locations:
            pattern = r'\b' + re.escape(loc.lower()) + r'\b'
            if re.search(pattern, first_sent):
                return loc

        return None

    def _strategy_sentence_pattern(self, response: str, obj: str, lang: str, stop_words: set) -> Optional[str]:
        """
        Extract location from sentence patterns about the object (last match — end-first).

        Handles responses like:
        - "The grape is on the counter"
        - "The grape remains on the counter"
        - "The grape fell onto the counter"

        Verb alternation is merged with target-language verbs for multilingual support.
        """
        obj_pattern = re.escape(obj.lower())

        # Merge English verbs with target-language verbs
        verbs_en = _LOCATION_VERBS["en"]
        verbs_local = _LOCATION_VERBS.get(lang, "")
        verbs = verbs_en if not verbs_local or lang == "en" else f"{verbs_en}|{verbs_local}"

        patterns = [
            rf'{obj_pattern} (?:{verbs}) (?:on|in|at|sitting on|onto|to) (?:the )?(\w+)',
            rf'{obj_pattern} (?:would be|will be|should be|must be) (?:on|in|at) (?:the )?(\w+)',
            rf'(?:{verbs}) (?:on|in|at) (?:the )?(\w+)',
            r'is (?:on|in|at) (?:the )?(\w+)(?:\.|$)',
        ]

        response_lower = response.lower()
        for pattern in patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                word = match.group(1)
                if word not in stop_words:
                    return word

        return None

    def _strategy_location_keyword(
        self,
        response: str,
        known_locations: List[str]
    ) -> Optional[str]:
        """
        Find known location words in response (last occurrence — end-first).

        Looks for exact matches of locations from the scenario,
        preferring the one that appears latest in the response.
        """
        response_lower = response.lower()

        best_location = None
        best_pos = -1

        # Check for exact location matches — find the last occurrence of each
        sorted_locations = sorted(known_locations, key=len, reverse=True)
        for location in sorted_locations:
            loc_lower = location.lower()
            pattern = r'\b' + re.escape(loc_lower) + r'\b'
            m = re_search_last(pattern, response_lower)
            if m and m.start() > best_pos:
                best_pos = m.start()
                best_location = location

        if best_location:
            return best_location

        # Also check synonyms (last occurrence)
        for synonym, canonical in self.location_synonyms.items():
            pattern = r'\b' + re.escape(synonym) + r'\b'
            m = re_search_last(pattern, response_lower)
            if m and m.start() > best_pos:
                best_pos = m.start()
                best_location = canonical

        return best_location

    def _strategy_last_word(self, response: str, stop_words: set) -> Optional[str]:
        """
        Extract last meaningful word as fallback.

        Handles responses like:
        - "Based on my analysis, the answer would be counter"
        - "Therefore, counter"
        """
        # Clean and split
        clean = re.sub(r'[^\w\s]', ' ', response).strip()
        words = clean.lower().split()

        # Filter and get last meaningful word
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]

        if meaningful_words:
            return meaningful_words[-1]

        # Fallback to any last word
        if words:
            return words[-1]

        return None

    def _normalize_location(self, location: str) -> str:
        """
        Normalize location to canonical form.

        Handles synonyms and case normalization.
        """
        location = location.lower().strip()

        # Remove common suffixes added by models
        location = re.sub(r'\.$', '', location)
        location = re.sub(r'^the\s+', '', location)

        # Check synonyms
        return self.location_synonyms.get(location, location)

    def _get_known_locations(self, task_params: Dict[str, Any]) -> List[str]:
        """
        Extract known locations from task parameters.

        Includes initial location and any locations visited by the container.
        """
        locations = set()

        # Initial location
        if 'initial_location' in task_params:
            locations.add(task_params['initial_location'])

        # Post-inversion container location
        if 'post_inversion_container_location' in task_params:
            locations.add(task_params['post_inversion_container_location'])

        # Expected answer
        if 'expected_answer' in task_params:
            locations.add(task_params['expected_answer'])

        # Step locations
        for step in task_params.get('steps', []):
            loc = step.get('object_location_after', '')
            if loc and loc != 'container':
                locations.add(loc)

        return [l for l in locations if l]

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'single_word',
            'answer_prefix',
            'bold_keyword',
            'first_sentence_location',
            'sentence_pattern',
            'location_keyword',
            'last_word'
        ]
