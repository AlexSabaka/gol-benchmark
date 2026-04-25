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
    normalize_unicode,
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

# ---------------------------------------------------------------------------
# Multilingual conclusion / reasoning anchors
#
# Object-tracking responses routinely lead the final answer with a
# reasoning anchor: "Conclusion:" / "Therefore, …" / "Висновок: …" /
# "Отже, …".  These are *reasoning* anchors (different from the shared
# ANSWER_LABELS — "answer/result/solution" — which are also accepted but
# much rarer in object-tracking outputs).  Identified from 129 annotated
# cases across EN/UA: Conclusion (43), Therefore (34), Відповідь (13),
# Отже (7), Тому (4), Висновок (3), Final Location (2), Final Answer (1),
# Deduction (1), Inference (2).  Extrapolated to ES/FR/DE/ZH using the
# same reasoning-closure vocabulary; annotation evidence for those
# languages still pending (Phase 8 follow-up).
# ---------------------------------------------------------------------------

_CONCLUSION_ANCHORS: Dict[str, List[str]] = {
    "en": [
        "conclusion", "therefore", "so", "thus", "hence",
        "final location", "final answer", "final position",
        "deduction", "inference", "in summary", "to summarize",
    ],
    "es": [
        "conclusión", "por lo tanto", "por tanto", "así que",
        "por consiguiente", "en conclusión", "finalmente",
        "en resumen", "ubicación final", "respuesta final",
    ],
    "fr": [
        "conclusion", "donc", "par conséquent", "ainsi",
        "finalement", "en conclusion", "en résumé",
        "emplacement final", "réponse finale",
    ],
    "de": [
        "schlussfolgerung", "daher", "also", "folglich",
        "somit", "schließlich", "zusammenfassend",
        "endgültiger ort", "endgültige antwort",
    ],
    "zh": [
        "结论", "因此", "所以", "最终", "总之", "综上",
        "最终位置", "最终答案",
    ],
    "ua": [
        "висновок", "відповідь", "отже", "тому",
        "таким чином", "остаточно", "насамкінець", "підсумовуючи",
        "остаточне місце", "остаточна відповідь",
    ],
}

# ---------------------------------------------------------------------------
# Multilingual preposition prefixes that immediately precede a location noun.
#
# Used by `_strategy_anchored_trailer` to capture the location span AFTER
# a reasoning anchor.  The capture group is (1-3 words) to handle multi-
# word locations common in UA ("на письмовому столі") and DE/FR compounds.
# ---------------------------------------------------------------------------

_LOCATION_PREPS: Dict[str, str] = {
    "en": r"(?:in|on|at|inside|within|atop|under|beneath|near|beside)\s+(?:the\s+)?",
    "es": r"(?:en|sobre|dentro\s+de|debajo\s+de|cerca\s+de|junto\s+a)\s+(?:el|la|los|las)?\s*",
    "fr": r"(?:dans|sur|sous|à\s+l['’]intérieur\s+de|près\s+de|au\s+fond\s+de)\s+(?:le|la|les|l['’])?\s*",
    "de": r"(?:in|auf|im|innerhalb|unter|neben)\s+(?:dem|der|den|das|einem|einer)?\s*",
    "zh": r"在\s*",
    "ua": r"(?:на|в|у|всередині|у\s+середині|в\s+середині|під|біля|поряд\s+з)\s+",
}

# Bold-trailer anchor dict: what precedes `**LOCATION**` when models
# write "…on the **counter**." / "…на **шафі**".  Used by the end-first
# pass in `_strategy_bold_keyword`.  Shorter than _LOCATION_PREPS because
# bold anchoring needs a tighter immediate-left context.
_BOLD_TRAILER_ANCHORS: Dict[str, str] = {
    "en": r"(?:the|on\s+the|in\s+the|at\s+the|inside\s+the|within\s+the)",
    "es": r"(?:el|la|los|las|en\s+el|en\s+la|sobre\s+el|sobre\s+la|dentro\s+del|dentro\s+de\s+la)",
    "fr": r"(?:le|la|les|l['’]|dans\s+le|dans\s+la|sur\s+le|sur\s+la)",
    "de": r"(?:dem|der|den|das|im|auf\s+dem|auf\s+der|in\s+dem|in\s+der)",
    "zh": r"在",
    "ua": r"(?:на|в|у|всередині|у\s+середині|в\s+середині)",
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
                parse_strategy='empty',
                error='Empty response'
            )

        lang = get_language(task_params)
        stop_words = _STOP_WORDS["en"] | _STOP_WORDS.get(lang, set())

        response = normalize_unicode(response.strip())
        known_locations = self._get_known_locations(task_params)
        obj = task_params.get('object', 'object')

        # Strip verification/confirmation tails for pattern-based strategies
        # so we don't grab locations from re-computation sections
        cleaned = strip_verification_tail(response)

        # Try each strategy in order
        strategies = [
            ('single_word', lambda: self._strategy_single_word(response, stop_words)),
            ('answer_prefix', lambda: self._strategy_answer_prefix(response, lang, stop_words)),
            ('bold_keyword', lambda: self._strategy_bold_keyword(response, known_locations, lang)),
            ('first_sentence_location', lambda: self._strategy_first_sentence_location(cleaned, known_locations)),
            # `anchored_trailer` targets the "Therefore, … in the X" / "Висновок: … на X"
            # pattern that dominated Phase 8 annotation misses (88 of 129 cases).  Runs
            # after first_sentence (which catches concise upfront answers) but before
            # sentence_pattern/location_keyword (which scan the full response and can
            # hit distractor containers).
            ('anchored_trailer', lambda: self._strategy_anchored_trailer(cleaned, known_locations, lang)),
            ('sentence_pattern', lambda: self._strategy_sentence_pattern(cleaned, obj, lang, stop_words)),
            ('location_keyword', lambda: self._strategy_location_keyword(cleaned, known_locations)),
            ('last_word', lambda: self._strategy_last_word(cleaned, stop_words, known_locations)),
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
            parse_strategy='fallback',
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
        lang: str = "en",
    ) -> Optional[str]:
        """
        Extract a bold-wrapped location.

        Two-pass strategy:
        1. **First-bold pass (existing behavior)** — concise models answer
           upfront: "The keys are on the **counter**. [distractors follow]."
           Later bolds in the explanation are distractors.
        2. **End-first anchored pass (added from Phase 8 annotation data)** —
           verbose models pattern as "…Therefore, the grape is in the
           **cabinet**." with the answer bolded at the END of a long
           explanation.  Only accepted when the bold is preceded by a
           location-preposition anchor (`the ** `, `on the ** `, `в **`,
           `на **`) AND the capture is a known location.  The anchor
           requirement avoids the format-only trap where `**Conclusion:**`
           headings get grabbed (86% capture_exact_rate on anchored vs.
           38% on bare bolds — 21-case EN/UA annotation sample).
        """
        # Pass 1: first-bold match (any known location anywhere in bold)
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

        # Pass 2: anchored end-first — require preposition anchor before
        # the bold capture so we don't grab `**Conclusion:**` / `**Reasoning:**`
        # headings.  Last match wins (end-first).
        anchor = _BOLD_TRAILER_ANCHORS.get(lang, _BOLD_TRAILER_ANCHORS["en"])
        anchored = re_search_last(
            rf"(?i){anchor}\s*\*\*([^*\n]{{1,40}})\*\*",
            response,
        )
        if anchored:
            candidate = anchored.group(1).lower().strip()
            for loc in known_locations:
                if loc.lower() in candidate or candidate in loc.lower():
                    return loc
            normalized = self._normalize_location(candidate)
            if normalized != candidate:
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

    def _strategy_anchored_trailer(
        self,
        response: str,
        known_locations: List[str],
        lang: str = "en",
    ) -> Optional[str]:
        """
        Extract location after a reasoning anchor in the tail of the response.

        Identifies the LAST occurrence of an anchor like `Conclusion:`,
        `Therefore,`, `Висновок:`, `Отже,` in the response, then searches
        forward from that anchor for a preposition-prefixed location
        capture (`in the X`, `на X`, `в X`).  The capture is accepted only
        when it matches (or is a synonym of) a known location, which
        filters out intermediate container references (`glass`, `cup`)
        that occur in reasoning text.

        Models routinely close verbose reasoning with the final answer
        trailer pattern: "Therefore, the coin is in the **counter**." or
        "Висновок: виноградинка знаходиться на письмовому столі."

        Phase 8 annotation data (129 cases, EN/UA): 88 of 129 cases have
        a trailer of this shape that current strategies miss because
        `location_keyword` walks the full response (picking up distractor
        containers) instead of being anchored to the final reasoning block.
        """
        anchors = list(_CONCLUSION_ANCHORS.get(lang, []))
        # Always merge in English anchors as fallback (models sometimes
        # reason in English even in non-English prompts).
        if lang != "en":
            anchors = anchors + _CONCLUSION_ANCHORS["en"]
        if not anchors:
            return None
        anchor_alt = "|".join(re.escape(a) for a in anchors)

        # Find LAST anchor position in response (end-first).  Word-bounded
        # on both sides so "con" doesn't match inside "connect".
        anchor_re = re.compile(rf"(?i)\b(?:{anchor_alt})\b")
        last_anchor_end = -1
        for m in anchor_re.finditer(response):
            last_anchor_end = m.end()
        if last_anchor_end < 0:
            return None

        # Scan the tail (after the anchor) up to ~400 chars for a
        # preposition-prefixed known-location capture.  End-first within
        # that window — the LAST known-location occurrence wins.
        tail = response[last_anchor_end:last_anchor_end + 400]
        prep = _LOCATION_PREPS.get(lang, _LOCATION_PREPS["en"])

        # Capture up to 3 words so multi-word UA locations like
        # "письмовому столі" / "на підлозі" are caught.  Also work on
        # English since "on the counter" still works with a trailing
        # greedy capture (extra words get stripped during normalization).
        capture_pat = rf"(?i){prep}((?:\w+[\s’'-]*){{1,3}}?\w+)"
        best_loc = None
        best_pos = -1
        for m in re.finditer(capture_pat, tail):
            candidate = m.group(1).strip().lower().rstrip(".,;:!?)—")
            # Strip markdown formatting
            candidate = candidate.replace("**", "").strip()
            # Try exact match against known_locations (longest-first)
            for loc in sorted(known_locations, key=len, reverse=True):
                loc_lower = loc.lower()
                if loc_lower == candidate or loc_lower in candidate.split():
                    if m.start() > best_pos:
                        best_pos = m.start()
                        best_loc = loc
                    break
            else:
                # Synonym fallback
                normalized = self._normalize_location(candidate)
                for loc in known_locations:
                    if loc.lower() == normalized:
                        if m.start() > best_pos:
                            best_pos = m.start()
                            best_loc = loc
                        break
        return best_loc

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

    def _strategy_last_word(
        self,
        response: str,
        stop_words: set,
        known_locations: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Extract last meaningful word as fallback, filtered against known locations.

        Pre-Phase-8 this strategy returned ANY last non-stopword token, which
        produced false positives like "within", "relative", "bottom", "top",
        "as" when the response's last clause wasn't a location.  Now the
        returned word must be in ``known_locations`` (or be a known synonym);
        if not, the strategy yields None and the caller falls through to
        ``fallback``.  This shifts the risk: rare cases where the model only
        mentions a location via paraphrase will now be unparseable instead
        of silently mis-parseable, which is the preferable trade per
        Phase 8 annotation data (5 junk-token extractions eliminated).

        Handles responses like:
        - "Based on my analysis, the answer would be counter" → "counter"
        - "Therefore, counter" → "counter"
        """
        # Clean and split
        clean = re.sub(r'[^\w\s]', ' ', response).strip()
        words = clean.lower().split()

        # Filter and get last meaningful word
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]

        if not meaningful_words and not words:
            return None

        candidate = meaningful_words[-1] if meaningful_words else words[-1]

        # Phase 8 tightening: require match against known locations (or a
        # known synonym canonicalizes to one).  Without this, last_word
        # catches prepositions/adjectives like "within", "relative",
        # "bottom" that end verbose trailing clauses.
        if known_locations:
            kl_lower = {loc.lower() for loc in known_locations}
            if candidate in kl_lower:
                return candidate
            normalized = self._normalize_location(candidate)
            if normalized in kl_lower:
                return normalized
            return None

        # Back-compat: when caller didn't pass known_locations (shouldn't
        # happen via parse(), but keep safe default for direct callers).
        return candidate

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

        # Expected answer (English + localized)
        if 'expected_answer' in task_params:
            locations.add(task_params['expected_answer'])
        if 'expected_answer_localized' in task_params:
            locations.add(task_params['expected_answer_localized'])

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
            'anchored_trailer',
            'sentence_pattern',
            'location_keyword',
            'last_word'
        ]
