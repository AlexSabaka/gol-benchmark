"""
Sally-Anne Response Parser

Multi-strategy parser for extracting container answers from model responses.
"""

import re
import json
from typing import Optional, Dict, Any
from ..base import ResponseParser, ParsedAnswer


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
    
    def parse(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedAnswer:
        """
        Parse model response to extract container answer.
        
        Args:
            response: Raw model response text
            metadata: Optional test case metadata (contains container_a, container_b)
            
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
        
        # Get known containers from metadata
        containers = []
        if metadata:
            if metadata.get('container_a'):
                containers.append(metadata['container_a'].lower())
            if metadata.get('container_b'):
                containers.append(metadata['container_b'].lower())
        
        # Strategy 1: LaTeX boxed answer - highest confidence
        parsed, strategy = self._try_boxed_extraction(response_clean)
        if parsed and self._is_valid_container(parsed, containers):
            return ParsedAnswer(
                value=self._normalize_container(parsed, metadata),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=1.0
            )
        
        # Strategy 2: Bold markdown (**answer**)
        parsed, strategy = self._try_bold_extraction(response_clean)
        if parsed and self._is_valid_container(parsed, containers):
            return ParsedAnswer(
                value=self._normalize_container(parsed, metadata),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.95
            )
        
        # Strategy 3: "Answer:" pattern
        parsed, strategy = self._try_answer_pattern(response_clean, containers)
        if parsed:
            return ParsedAnswer(
                value=self._normalize_container(parsed, metadata),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.9
            )
        
        # Strategy 4: "will look in/for the [container]" pattern
        parsed, strategy = self._try_look_pattern(response_clean, containers)
        if parsed:
            return ParsedAnswer(
                value=self._normalize_container(parsed, metadata),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.85
            )
        
        # Strategy 5: First sentence container mention
        parsed, strategy = self._try_first_sentence(response_clean, containers)
        if parsed:
            return ParsedAnswer(
                value=self._normalize_container(parsed, metadata),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.8
            )
        
        # Strategy 6: JSON extraction
        parsed, strategy = self._try_json_extraction(response_clean)
        if parsed and self._is_valid_container(parsed, containers):
            return ParsedAnswer(
                value=self._normalize_container(parsed, metadata),
                raw_response=response_clean,
                parse_strategy=strategy,
                confidence=0.75
            )
        
        # Strategy 7: Direct container match
        parsed, strategy = self._try_direct_container_match(response_clean, containers, metadata)
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
        """Check if text contains a valid container name."""
        if not text:
            return False
        text_lower = text.lower().strip()
        
        # Direct match
        if text_lower in containers:
            return True
        
        # Check if any container is in the text
        for container in containers:
            if container in text_lower:
                return True
        
        # Check synonyms
        for canonical, synonyms in self.container_synonyms.items():
            if text_lower in [s.lower() for s in synonyms]:
                return True
        
        return False
    
    def _try_boxed_extraction(self, response: str) -> tuple[Optional[str], str]:
        """Try to extract answer from LaTeX \\boxed{} format."""
        patterns = [
            (r'\\boxed\{\\text\{([^}]+)\}\}', 'boxed_text'),
            (r'\\boxed\{([^}]+)\}', 'boxed'),
        ]
        
        for pattern, strategy in patterns:
            match = re.search(pattern, response)
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
        """Try to extract answer from 'Answer:' pattern."""
        response_lower = response.lower()
        
        # Pattern: "Answer: [container]" or "**Answer:** [container]"
        patterns = [
            r'\*?\*?answer\*?\*?\s*:\s*(?:the\s+)?(\w+)',
            r'answer\s+is\s+(?:the\s+)?(\w+)',
            r'answer\s+is\s+(?:the\s+)?["\']?(\w+)["\']?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_lower)
            if match:
                answer = match.group(1).strip()
                if answer in containers or self._is_valid_container(answer, containers):
                    return answer, "answer_pattern"
        
        return None, ""
    
    def _try_look_pattern(self, response: str, containers: list) -> tuple[Optional[str], str]:
        """Try to extract from 'will look in/for the [container]' patterns."""
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
            match = re.search(pattern, response_lower)
            if match:
                answer = match.group(1).strip()
                if answer in containers:
                    return answer, "look_pattern"
        
        return None, ""
    
    def _try_first_sentence(self, response: str, containers: list) -> tuple[Optional[str], str]:
        """Try to extract container from the first sentence."""
        # Get first sentence (up to first period, question mark, or newline)
        first_sent_match = re.match(r'^[^.!?\n]+', response.strip())
        if not first_sent_match:
            return None, ""
        
        first_sentence = first_sent_match.group(0).lower()
        
        # Check which container is mentioned in first sentence
        for container in containers:
            if container in first_sentence:
                # Make sure it's in a context like "in the X" or "the X"
                if re.search(rf'(?:in\s+the\s+|the\s+)\*?\*?{re.escape(container)}\*?\*?', first_sentence):
                    return container, "first_sentence"
        
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
    
    def _try_direct_container_match(self, response: str, containers: list, metadata: Dict) -> tuple[Optional[str], str]:
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
                # Normalize to original case from metadata
                if metadata:
                    if best == metadata.get('container_a', '').lower():
                        return metadata['container_a'], "direct_match"
                    if best == metadata.get('container_b', '').lower():
                        return metadata['container_b'], "direct_match"
                return best, "direct_match"
        
        return None, ""
    
    def _normalize_container(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Normalize container name to match expected format.
        """
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Remove common prefixes
        prefixes = ['the ', 'a ', 'an ', 'in ', 'at ']
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                text_lower = text_lower[len(prefix):].strip()
        
        # If we have metadata, return the properly-cased container name
        if metadata:
            container_a = metadata.get('container_a', '').lower()
            container_b = metadata.get('container_b', '').lower()
            
            if text_lower == container_a or container_a in text_lower:
                return metadata['container_a']
            if text_lower == container_b or container_b in text_lower:
                return metadata['container_b']
        
        return text_lower
