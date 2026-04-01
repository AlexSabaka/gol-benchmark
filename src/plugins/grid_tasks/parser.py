"""
Grid Tasks Response Parser

Multi-strategy parser for extracting answers from model responses.
Supports numeric and text answers with various formatting patterns.
"""

import json
import re
from typing import Any, Dict, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    build_answer_label_re,
    get_language,
    re_search_last,
)


class GridTasksResponseParser(ResponseParser):
    """Parse model responses for grid task answers."""
    
    def get_strategies(self) -> list[str]:
        """Return list of parsing strategies in order of priority."""
        return [
            'boxed_latex',      # \boxed{answer}
            'bold_markdown',    # **answer**
            'answer_pattern',   # Answer: X or The answer is X
            'json_extraction',  # {"answer": "X"}
            'code_block',       # ```answer```
            'quoted',           # "answer" or 'answer'
            'last_line',        # Last non-empty line
            'last_number',      # Last numeric value
        ]
    
    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse model response using multiple strategies.
        
        Args:
            response: Raw model response text
            task_params: Task parameters including expected_answer type info
        
        Returns:
            ParsedAnswer with extracted value, strategy, and confidence
        """
        lang = get_language(task_params)
        # Sort labels longest-first so "final answer" is tried before "answer"
        raw_labels = build_answer_label_re(lang)
        self._label_re = "|".join(
            sorted(raw_labels.split("|"), key=len, reverse=True)
        )

        if not response or not response.strip():
            return ParsedAnswer(
                value=None,
                raw_response=response,
                parse_strategy="empty_response",
                confidence=0.0,
                error="Empty or whitespace-only response"
            )
        
        # Normalize Unicode spaces to regular spaces
        # \u00A0 = non-breaking space, \u202F = narrow no-break space
        response = re.sub(r'[\u00A0\u202F\u2009\u200B]', ' ', response)
        
        # Try strategies in order
        strategies = [
            ('boxed_latex', self._try_boxed_latex),
            ('bold_markdown', self._try_bold_markdown),
            ('answer_pattern', self._try_answer_pattern),
            ('json_extraction', self._try_json_extraction),
            ('code_block', self._try_code_block),
            ('quoted', self._try_quoted),
            ('last_line', self._try_last_line),
            ('last_number', self._try_last_number),
        ]
        
        for strategy_name, strategy_func in strategies:
            result = strategy_func(response)
            if result is not None:
                return ParsedAnswer(
                    value=result['value'],
                    raw_response=response,
                    parse_strategy=strategy_name,
                    confidence=result['confidence'],
                    error=None
                )
        
        # All strategies failed
        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy="no_match",
            confidence=0.0,
            error="No parsing strategy succeeded"
        )
    
    def _try_boxed_latex(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from LaTeX \\boxed{} notation (last match)."""
        pattern = r'\\boxed\{([^}]+)\}'
        match = re_search_last(pattern, response)
        if match:
            value = match.group(1).strip()
            return {'value': self._normalize_value(value), 'confidence': 1.0}
        return None
    
    def _try_bold_markdown(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from **bold** markdown (last match — end-first)."""
        pattern = r'\*\*([^*]+)\*\*'
        matches = re.findall(pattern, response)
        if matches:
            # Filter out common non-answer bold items
            non_answer_patterns = [
                r'^\$[\d,]+',        # Dollar amounts like $8,678.19
                r'^[\d,]+$',         # Plain numbers
                r'^[\d,]+\.\d+$',    # Decimal numbers
                r'^Q\d+$',           # Quarter references like Q2
                r'^Note:?',          # Notes
                r'^Warning:?',       # Warnings
            ]

            # Iterate from end (end-first principle)
            for match in reversed(matches):
                match_stripped = match.strip()
                is_non_answer = any(re.match(p, match_stripped) for p in non_answer_patterns)
                if not is_non_answer and len(match_stripped) > 1:
                    return {'value': self._normalize_value(match_stripped), 'confidence': 0.95}

            # If all matches were filtered, take the last one anyway
            value = matches[-1].strip()
            return {'value': self._normalize_value(value), 'confidence': 0.85}
        return None
    
    def _try_answer_pattern(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from common patterns (last match — end-first)."""
        label_re = self._label_re
        patterns = [
            rf'(?:^|\n)\s*(?:\w+\s+)?(?:{label_re})\s*(?:is\s*)?:?\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re_search_last(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = value.rstrip('.,;!')
                return {'value': self._normalize_value(value), 'confidence': 0.9}
        return None
    
    def _try_json_extraction(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from JSON format."""
        # Look for JSON objects
        json_pattern = r'\{[^{}]*"answer"[^{}]*\}'
        matches = re.findall(json_pattern, response, re.IGNORECASE)
        
        for match in matches:
            try:
                data = json.loads(match)
                if 'answer' in data:
                    return {'value': self._normalize_value(str(data['answer'])), 'confidence': 0.85}
                elif 'Answer' in data:
                    return {'value': self._normalize_value(str(data['Answer'])), 'confidence': 0.85}
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _try_code_block(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from code blocks."""
        # Pattern: ```answer``` or ```python\nanswer\n```
        pattern = r'```(?:\w+)?\s*([^`]+)\s*```'
        matches = re.findall(pattern, response)
        if matches:
            # Take the last code block
            value = matches[-1].strip()
            return {'value': self._normalize_value(value), 'confidence': 0.8}
        return None
    
    def _try_quoted(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from quoted text."""
        # Pattern: "answer" or 'answer'
        patterns = [
            r'"([^"]+)"',
            r"'([^']+)'",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            if matches:
                # Take the last quoted text
                value = matches[-1].strip()
                # Only accept if it looks like a reasonable answer (not a full sentence)
                if len(value.split()) <= 5:
                    return {'value': self._normalize_value(value), 'confidence': 0.75}
        return None
    
    def _try_last_line(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract the last non-empty line as answer."""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        if lines:
            value = lines[-1]
            # Remove multilingual answer-label prefixes
            label_re = self._label_re
            prefix_match = re.match(
                rf'(?:\w+\s+)?(?:{label_re})\s*(?:is\s*)?:?\s*',
                value,
                re.IGNORECASE,
            )
            if prefix_match:
                value = value[prefix_match.end():].strip()
            # Remove trailing punctuation
            value = value.rstrip('.,;!')
            return {'value': self._normalize_value(value), 'confidence': 0.7}
        return None
    
    def _try_last_number(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract the last numeric value (end-first principle)."""
        pattern = r'-?\d+(?:\.\d+)?'
        match = re_search_last(pattern, response)
        if match:
            value = match.group(0)
            return {'value': self._normalize_value(value), 'confidence': 0.6}
        return None
    
    def _normalize_value(self, value: str) -> str:
        """Normalize extracted value."""
        if not value:
            return ""
        
        # Remove extra whitespace
        value = ' '.join(value.split())
        
        # Remove common artifacts
        value = value.strip('.,;!?')
        
        # Try to normalize numeric values
        try:
            # If it's a number, format consistently
            if '.' in value:
                num = float(value)
                # Keep 2 decimal places for floats
                return f"{num:.2f}"
            else:
                # Keep as integer
                num = int(value)
                return str(num)
        except ValueError:
            # Not a number, return as-is
            pass
        
        return value
