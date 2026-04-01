"""
Linda Fallacy Response Parser

Multi-strategy parser for extracting rankings from model responses.
Handles various response formats including numbered lists and probability keywords.
"""

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import get_language


class LindaResponseParser(ResponseParser):
    """
    Multi-strategy parser for Linda Fallacy model responses.

    Parsing Strategies:
    1. Explicit ranking section: Look for RANKING/CLASIFICACIÓN headers
    2. Numbered list fallback: Find numbered lists anywhere
    3. Probability keywords: Extract lines with probability mentions
    4. Sentence extraction: Find statements about the persona
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response to extract rankings.

        Args:
            response: Raw model response string
            task_params: Task parameters (for reference items)

        Returns:
            ParsedAnswer with extracted rankings dict or error
        """
        lang = get_language(task_params)

        if not response:
            return ParsedAnswer(
                value={'rankings': [], 'parse_error': 'Empty response'},
                raw_response=response or "",
                parse_strategy='failed',
                confidence=0.1,
                error='Empty response from model'
            )

        # Try each parsing strategy in order (with confidence scores)
        strategies = [
            ('explicit_ranking_section', self._strategy_explicit_ranking, 0.90),
            ('numbered_list_fallback', self._strategy_numbered_list, 0.80),
            ('probability_keyword', self._strategy_probability_keywords, 0.70),
            ('sentence_extraction', self._strategy_sentence_extraction, 0.55),
        ]

        for name, strategy_func, confidence in strategies:
            try:
                rankings = strategy_func(response)
                if rankings and len(rankings) >= 6:
                    # Deduplicate and clean
                    final_rankings = self._deduplicate_rankings(rankings)
                    if len(final_rankings) >= 6:
                        return ParsedAnswer(
                            value={
                                'rankings': final_rankings,
                                'parse_strategy': name,
                                'parse_error': None
                            },
                            raw_response=response,
                            parse_strategy=name,
                            confidence=confidence
                        )
            except Exception:
                continue

        # No valid rankings found
        return ParsedAnswer(
            value={'rankings': [], 'parse_error': 'No rankings found'},
            raw_response=response,
            parse_strategy='failed',
            confidence=0.1,
            error='All parsing strategies failed'
        )

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'explicit_ranking_section',
            'numbered_list_fallback',
            'probability_keyword',
            'sentence_extraction'
        ]

    def _clean_item(self, text: str) -> str:
        """Clean a ranking item by removing explanations and formatting."""
        # Remove bold/italic markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # Remove likelihood markers
        text = re.sub(
            r'\s*[:\-–—]\s*(?:Most|Least|Very|Highly)?\s*(?:Likely|Unlikely|Probable|Improbable|Possible)\s*',
            '', text, flags=re.IGNORECASE
        )

        # Remove parenthetical explanations
        text = re.sub(r'\s*\([^)]*(?:likely|probable|fit|match|possible)[^)]*\)\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*\([^)]*\d+[^)]*\)\s*$', '', text)
        text = re.sub(r'\s*\([^)]*\)\s*$', '', text)

        # Split on dashes (before explanations)
        for dash in ['–', '—', ' - ']:
            if dash in text:
                text = text.split(dash)[0].strip()
                break

        # Split on colon if present
        if ':' in text and ' and ' not in text.split(':')[0]:
            text = text.split(':')[0].strip()

        # Clean up sentence fragments
        for delimiter in ['. This', '. It', '. He', '. She', '. Given', '. While']:
            if delimiter in text:
                text = text.split(delimiter)[0].strip()
                break

        return text.strip()

    def _strategy_explicit_ranking(self, response: str) -> List[str]:
        """Strategy 1: Look for explicit ranking sections with headers."""
        ranking_keywords = [
            'RANKING', 'CLASIFICACIÓN', 'CLASSEMENT',
            'RANKING:', 'CLASIFICACIÓN:', 'CLASSEMENT:',
            'RANGFOLGE', 'RANGFOLGE:',
            '排名', '排名:',
            'РЕЙТИНГ', 'РЕЙТИНГ:',
        ]
        reasoning_keywords = [
            'REASONING', 'RAZONAMIENTO', 'RAISONNEMENT',
            'BEGRÜNDUNG', '推理', 'ОБҐРУНТУВАННЯ',
        ]

        ranking_pattern = f"(?:{'|'.join(ranking_keywords)})\\s*(.*?)(?=(?:{'|'.join(reasoning_keywords)}):|$)"
        ranking_match = re.search(ranking_pattern, response, re.DOTALL | re.IGNORECASE)

        if not ranking_match:
            return []

        ranking_text = ranking_match.group(1).strip()
        lines = ranking_text.split('\n')
        rankings = []

        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                item_text = re.sub(r'^\d+\.\s*', '', line).strip()
                item_text = self._clean_item(item_text)
                if item_text and len(item_text) > 3:
                    rankings.append(item_text)

        return rankings

    def _strategy_numbered_list(self, response: str) -> List[str]:
        """Strategy 2: Find numbered lists anywhere in response."""
        lines = response.split('\n')
        rankings = []

        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                item_text = re.sub(r'^\d+\.\s*', '', line).strip()
                item_text = self._clean_item(item_text)
                if item_text and len(item_text) > 3:
                    rankings.append(item_text)

        return rankings

    def _strategy_probability_keywords(self, response: str) -> List[str]:
        """Strategy 3: Extract lines with probability keywords."""
        lines = response.split('\n')
        rankings = []

        prob_keywords = [
            'most probable', 'least probable',
            'más probable', 'menos probable',
            'plus probable', 'moins probable',
            'wahrscheinlichste', 'unwahrscheinlichste', 'am wahrscheinlichsten',
            '最可能', '最不可能',
            'найбільш ймовірно', 'найменш ймовірно',
        ]

        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in prob_keywords):
                rankings.append(self._clean_item(line))

        return rankings

    def _strategy_sentence_extraction(self, response: str) -> List[str]:
        """Strategy 4: Extract sentences about the persona."""
        sentences = re.split(r'[.!?]', response)
        rankings = []
        seen_items = set()

        statement_keywords = [
            'is a', 'works', 'trabaja', 'es ', 'est ', 'travaille',
            'ist ein', 'arbeitet',
            '是', '工作',
            'є', 'працює',
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and any(kw in sentence.lower() for kw in statement_keywords):
                clean = self._clean_item(sentence)
                sentence_key = re.sub(r'[^a-zA-Z0-9]', '', clean.lower())
                if sentence_key not in seen_items and len(clean) > 5:
                    rankings.append(clean)
                    seen_items.add(sentence_key)

        return rankings[:10]

    def _deduplicate_rankings(self, rankings: List[str]) -> List[str]:
        """Remove exact and fuzzy duplicates from rankings.

        Uses word-level Jaccard similarity (not character-level) so that
        "bank teller" and "bank" are not treated as near-duplicates.
        """
        final = []
        seen_exact = set()
        seen_normalized = set()

        for ranking in rankings:
            if ranking in seen_exact:
                continue

            normalized = re.sub(r'[^a-zA-Z0-9\s]', '', ranking.lower()).strip()
            if len(normalized) < 5:
                continue

            norm_words = set(normalized.split())

            # Check for fuzzy duplicates using word-level Jaccard
            is_duplicate = False
            for existing in final:
                existing_norm = re.sub(r'[^a-zA-Z0-9\s]', '', existing.lower()).strip()
                existing_words = set(existing_norm.split())

                # Substring containment at word level
                if norm_words <= existing_words or existing_words <= norm_words:
                    is_duplicate = True
                    break

                # Word-level Jaccard similarity
                union = norm_words | existing_words
                if union:
                    similarity = len(norm_words & existing_words) / len(union)
                    if similarity > 0.85:
                        is_duplicate = True
                        break

            norm_key = re.sub(r'[^a-zA-Z0-9]', '', normalized)
            if is_duplicate or norm_key in seen_normalized:
                continue

            final.append(ranking)
            seen_exact.add(ranking)
            seen_normalized.add(norm_key)

        return final[:10]
