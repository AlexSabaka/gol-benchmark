"""
Grid Tasks Response Parser

Multi-strategy parser for extracting answers from model responses.
Supports numeric and text answers with various formatting patterns.
"""

import json
import re
from typing import Any, Dict, Optional

from src.plugins.base import ParsedAnswer, ResponseParser


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
            'first_number',     # First numeric value
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
        if not response or not response.strip():
            return ParsedAnswer(
                value=None,
                raw_response=response,
                parse_strategy="empty_response",
                confidence=0.0,
                error="Empty or whitespace-only response"
            )
        
        # Try strategies in order
        strategies = [
            ('boxed_latex', self._try_boxed_latex),
            ('bold_markdown', self._try_bold_markdown),
            ('answer_pattern', self._try_answer_pattern),
            ('json_extraction', self._try_json_extraction),
            ('code_block', self._try_code_block),
            ('quoted', self._try_quoted),
            ('last_line', self._try_last_line),
            ('first_number', self._try_first_number),
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
        """Try to extract answer from LaTeX \\boxed{} notation."""
        # Pattern: \boxed{answer}
        pattern = r'\\boxed\{([^}]+)\}'
        match = re.search(pattern, response)
        if match:
            value = match.group(1).strip()
            return {'value': self._normalize_value(value), 'confidence': 1.0}
        return None
    
    def _try_bold_markdown(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from **bold** markdown."""
        # Pattern: **answer**
        pattern = r'\*\*([^*]+)\*\*'
        matches = re.findall(pattern, response)
        if matches:
            # Take the last bold text as answer
            value = matches[-1].strip()
            return {'value': self._normalize_value(value), 'confidence': 0.95}
        return None
    
    def _try_answer_pattern(self, response: str) -> Optional[Dict[str, Any]]:
        """Try to extract answer from common patterns like 'Answer: X' or 'The answer is X'."""
        patterns = [
            r'(?:^|\n)Answer:\s*([^\n]+)',
            r'(?:^|\n)The answer is:?\s*([^\n]+)',
            r'(?:^|\n)Final answer:\s*([^\n]+)',
            r'(?:^|\n)Result:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Remove trailing punctuation
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
            # Remove common prefixes
            for prefix in ['Answer:', 'The answer is:', 'Final answer:', 'Result:']:
                if value.lower().startswith(prefix.lower()):
                    value = value[len(prefix):].strip()
            # Remove trailing punctuation
            value = value.rstrip('.,;!')
            return {'value': self._normalize_value(value), 'confidence': 0.7}
        return None
    
    def _try_first_number(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract the first numeric value (useful for numeric questions)."""
        # Pattern: number (integer or decimal)
        pattern = r'-?\d+(?:\.\d+)?'
        match = re.search(pattern, response)
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
