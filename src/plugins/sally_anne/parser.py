"""
Sally-Anne Response Parser

Multi-strategy parser for extracting container answers from model responses.
"""

import re
import json
from typing import Dict, Any, Optional
from ..base import ResponseParser, ParsedAnswer
from ..parse_utils import re_search_last, strip_verification_tail


class SallyAnneResponseParser(ResponseParser):
    """
    Parser for Sally-Anne test responses.
    
    Uses multi-strategy approach to extract container names:
    1. Boxed answer (\\boxed{basket})
    2. Bold markdown (**basket**)
    3. "Answer:" pattern
    4. "will look in the [container]" pattern
    5. First sentence container mention
    6. JSON extraction
    7. Direct container match with context weighting
    """
    
    def __init__(self):
        # Common container synonyms/variations
        self.container_synonyms = {
            'basket': ['basket', 'hamper', 'wicker basket'],
            'box': ['box', 'container', 'storage box', 'carton'],
            'drawer': ['drawer', 'cabinet drawer'],
            'cupboard': ['cupboard', 'cabinet', 'closet'],
            'bag': ['bag', 'purse', 'sack', 'tote'],
            'pocket': ['pocket', 'coat pocket', 'pants pocket'],
        }
    
    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse model response to extract container answer.

        Args:
            response: Raw model response text
            task_params: Task parameters (contains container_a, container_b)

        Returns:
            ParsedAnswer with extracted container name
        """
        if not response or not response.strip():
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy="none",
                confidence=0.0,
                error="Empty response"
            )
        
        response_clean = response.strip()
        
        # Get known containers from task_params
        containers = []
        if task_params:
            if task_params.get('container_a'):
                containers.append(task_params['container_a'].lower())
            if task_params.get('container_b'):
                containers.append(task_params['container_b'].lower())
        
        # Strategy 1: LaTeX boxed answer - highest confidence
        parsed, strategy = self._try_boxed_extraction(response_clean)
        if parsed and self._is_valid_container(parsed, containers):
            return ParsedAnswer(
                value=self._normalize_container(parsed, task_params),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=1.0
            )
        
        # Strategy 2: Bold markdown (**answer**)
        parsed, strategy = self._try_bold_extraction(response_clean)
        if parsed and self._is_valid_container(parsed, containers):
            return ParsedAnswer(
                value=self._normalize_container(parsed, task_params),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.95
            )
        
        # Strategy 3: "Answer:" pattern
        parsed, strategy = self._try_answer_pattern(response_clean, containers)
        if parsed:
            return ParsedAnswer(
                value=self._normalize_container(parsed, task_params),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.9
            )
        
        # Strategy 4: "will look in/for the [container]" pattern
        parsed, strategy = self._try_look_pattern(response_clean, containers)
        if parsed:
            return ParsedAnswer(
                value=self._normalize_container(parsed, task_params),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.85
            )
        
        # Strategy 5: Last sentence container mention (end-first)
        # Strip verification/confirmation tails so we don't grab containers
        # from re-computation sections
        cleaned = strip_verification_tail(response_clean)
        parsed, strategy = self._try_last_sentence(cleaned, containers)
        if parsed:
            return ParsedAnswer(
                value=self._normalize_container(parsed, task_params),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.8
            )

        # Strategy 6: JSON extraction
        parsed, strategy = self._try_json_extraction(response_clean)
        if parsed and self._is_valid_container(parsed, containers):
            return ParsedAnswer(
                value=self._normalize_container(parsed, task_params),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.75
            )

        # Strategy 7: Direct container match
        parsed, strategy = self._try_direct_container_match(cleaned, containers, task_params)
        if parsed:
            return ParsedAnswer(
                value=parsed,
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.7
            )
        
        # Fallback: no valid answer found
        return ParsedAnswer(
            value=None,
            raw_response=response_clean,
            parse_strategy="fallback",
            confidence=0.0,
            error="Could not extract container from response"
        )
    
    def _is_valid_container(self, text: str, containers: list) -> bool:
        """Check if text contains a valid container name (word-boundary match)."""
        if not text:
            return False
        text_lower = text.lower().strip()

        # Direct match
        if text_lower in containers:
            return True

        # Check if any container appears as a whole word in the text
        for container in containers:
            if re.search(r'\b' + re.escape(container) + r'\b', text_lower):
                return True

        # Check synonyms
        for synonyms in self.container_synonyms.values():
            if text_lower in [s.lower() for s in synonyms]:
                return True

        return False
    
    def _try_boxed_extraction(self, response: str) -> tuple[Optional[str], str]:
        """Try to extract answer from LaTeX \\boxed{} format (last match)."""
        patterns = [
            (r'\\boxed\{\\text\{([^}]+)\}\}', 'boxed_text'),
            (r'\\boxed\{([^}]+)\}', 'boxed'),
        ]

        for pattern, strategy in patterns:
            match = re_search_last(pattern, response)
            if match:
                return match.group(1).strip(), strategy

        return None, ""
    
    def _try_bold_extraction(self, response: str) -> tuple[Optional[str], str]:
        """Try to extract answer from markdown bold **answer**."""
        # Pattern: **word** - capture the bolded word
        matches = re.findall(r'\*\*([^*]+)\*\*', response)
        
        # Return the last bolded word (usually the answer)
        for match in reversed(matches):
            text = match.strip().lower()
            # Skip if it's a long phrase (likely emphasis, not answer)
            if len(text.split()) <= 3:
                return match.strip(), "bold_markdown"
        
        return None, ""
    
    def _try_answer_pattern(self, response: str, containers: list) -> tuple[Optional[str], str]:
        """Try to extract answer from 'Answer:' pattern (last match)."""
        response_lower = response.lower()

        # Pattern: "Answer: [container]" or "**Answer:** [container]"
        patterns = [
            r'\*?\*?answer\*?\*?\s*:\s*(?:the\s+)?(\w+)',
            r'answer\s+is\s+(?:the\s+)?(\w+)',
            r'answer\s+is\s+(?:the\s+)?["\']?(\w+)["\']?',
        ]

        for pattern in patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                answer = match.group(1).strip()
                if answer in containers or self._is_valid_container(answer, containers):
                    return answer, "answer_pattern"

        return None, ""
    
    def _try_look_pattern(self, response: str, containers: list) -> tuple[Optional[str], str]:
        """Try to extract from 'will look in/for the [container]' patterns (last match)."""
        response_lower = response.lower()

        patterns = [
            r'will\s+(?:naturally\s+)?look\s+(?:for\s+(?:the\s+\w+\s+)?)?in\s+the\s+(\w+)',
            r'will\s+(?:naturally\s+)?look\s+for\s+(?:his|her|the|their)\s+\w+\s+in\s+(?:the\s+)?(\w+)',
            r'will\s+search\s+(?:for\s+(?:the\s+\w+\s+)?)?in\s+the\s+(\w+)',
            r'will\s+(?:check|search)\s+the\s+(\w+)',
            r'look\s+in\s+the\s+(\w+)',
            r'search\s+in\s+the\s+(\w+)',
            r'he\s+will\s+look\s+in\s+the\s+(\w+)',
            r'she\s+will\s+look\s+in\s+the\s+(\w+)',
        ]

        for pattern in patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                answer = match.group(1).strip()
                if answer in containers:
                    return answer, "look_pattern"

        return None, ""
    
    def _try_last_sentence(self, response: str, containers: list) -> tuple[Optional[str], str]:
        """Try to extract container from the last sentence (end-first)."""
        # Split into sentences and check from end
        sentences = re.split(r'[.!?\n]+', response.strip())
        for sent in reversed(sentences):
            sent_lower = sent.strip().lower()
            if not sent_lower:
                continue
            for container in containers:
                if re.search(r'\b' + re.escape(container) + r'\b', sent_lower):
                    # Make sure it's in a context like "in the X" or "the X"
                    if re.search(rf'(?:in\s+the\s+|the\s+)\*?\*?{re.escape(container)}\*?\*?', sent_lower):
                        return container, "last_sentence"

        return None, ""
    
    def _try_json_extraction(self, response: str) -> tuple[Optional[str], str]:
        """Try to extract answer from JSON format."""
        json_patterns = [
            r'\{[^}]*"answer"\s*:\s*"([^"]+)"[^}]*\}',
            r'\{[^}]*"location"\s*:\s*"([^"]+)"[^}]*\}',
            r'\{[^}]*"container"\s*:\s*"([^"]+)"[^}]*\}',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip(), "json"
        
        return None, ""
    
    def _try_direct_container_match(self, response: str, containers: list, task_params: Dict) -> tuple[Optional[str], str]:
        """
        Count occurrences of each container and use context to pick the answer.
        
        This handles cases where the model discusses both containers but the answer
        is the one associated with the belief (not reality).
        """
        response_lower = response.lower()
        
        # Count occurrences with context weighting
        scores = {}
        for container in containers:
            # Base count
            count = response_lower.count(container)
            
            # Boost for answer-related context
            answer_contexts = [
                f'look in the {container}',
                f'look for.*in.*{container}',
                f'search.*{container}',
                f'answer.*{container}',
                f'in the {container}',
                f'the {container}\\.',  # ends sentence
                f'\\*\\*{container}\\*\\*',  # bolded
            ]
            
            context_score = 0
            for ctx in answer_contexts:
                if re.search(ctx, response_lower):
                    context_score += 2
            
            scores[container] = count + context_score
        
        # Pick the container with highest score
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                # Normalize to original case from task_params
                if task_params:
                    if best == task_params.get('container_a', '').lower():
                        return task_params['container_a'], "direct_match"
                    if best == task_params.get('container_b', '').lower():
                        return task_params['container_b'], "direct_match"
                return best, "direct_match"
        
        return None, ""
    
    def _normalize_container(self, text: str, task_params: Optional[Dict[str, Any]] = None) -> str:
        """Normalize container name to match expected format (word-boundary safe)."""
        if not text:
            return None

        text_lower = text.lower().strip()

        # Remove common prefixes
        prefixes = ['the ', 'a ', 'an ', 'in ', 'at ']
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                text_lower = text_lower[len(prefix):].strip()

        # If we have task_params, return the properly-cased container name
        # Use word-boundary match to avoid "basket" matching "basketball"
        if task_params:
            container_a = task_params.get('container_a', '').lower()
            container_b = task_params.get('container_b', '').lower()

            if container_a and (text_lower == container_a or re.search(r'\b' + re.escape(container_a) + r'\b', text_lower)):
                return task_params['container_a']
            if container_b and (text_lower == container_b or re.search(r'\b' + re.escape(container_b) + r'\b', text_lower)):
                return task_params['container_b']

        return text_lower
