"""
Carwash Paradox – Response Parser

Extracts the model's answer (drive / walk / other) from free-form text using
multiple strategies, ordered by specificity.

Resolution strategy:
 1. Explicit boxed answer: \\boxed{drive} / \\boxed{walk}
 2. Bold / header answer: **drive** / **walk**
 3. Keyword "Answer:" / "Recommendation:" / "Decision:" line
 4. Direct keyword search — looks for the first strong signal word
 5. Sentence-level: first sentence that mentions drive / walk
 6. Fallback: raw response snippet

Match values returned:
  "drive"  -> correct
  "walk"   -> naive trap
  "other"  -> wrong / unclear
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.plugins.base import ResponseParser, ParsedAnswer

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

DRIVE_KEYWORDS = [
    r"\bdrive\b",
    r"\bdriving\b",
    r"\btake\s+(?:your|the|my)\s+car\b",
    r"\buse\s+(?:your|the|my)\s+car\b",
    r"\bgo\s+by\s+car\b",
    r"\bgo\s+in\s+(?:your|the|my)\s+car\b",
    r"\bget\s+in\s+(?:your|the|my)\s+car\b",
    r"\bcar\b.*\bneed(?:s?)\b",
    r"\bbring\s+(?:your|the|my)\s+car\b",
    r"\btake\s+it\s+there\b",
    r"\bdrive\s+it\s+there\b",
]

WALK_KEYWORDS = [
    r"\bwalk\b",
    r"\bwalking\b",
    r"\bon\s+foot\b",
    r"\bfoot\b",
    r"\bstroll\b",
    r"\bpedestrian\b",
]

# negative tokens that flip a "walk" match (e.g. "don't walk")
NEGATION = re.compile(
    r"\b(don'?t|do not|shouldn'?t|should not|no need to|not necessary to)\s+walk\b",
    re.IGNORECASE,
)


def _score(text: str) -> Optional[str]:
    """Return 'drive', 'walk', or None based on keyword presence."""
    t = text.lower()
    has_drive = any(re.search(kw, t) for kw in DRIVE_KEYWORDS)
    has_walk = any(re.search(kw, t) for kw in WALK_KEYWORDS)
    negated_walk = bool(NEGATION.search(t))

    if has_drive and (not has_walk or negated_walk):
        return "drive"
    if has_walk and not has_drive and not negated_walk:
        return "walk"
    if has_drive and has_walk and not negated_walk:
        # Both present — check which one comes first as the recommendation
        drive_pos = min(
            (m.start() for kw in DRIVE_KEYWORDS for m in [re.search(kw, t)] if m),
            default=len(t),
        )
        walk_pos = min(
            (m.start() for kw in WALK_KEYWORDS for m in [re.search(kw, t)] if m),
            default=len(t),
        )
        return "drive" if drive_pos < walk_pos else "walk"
    return None


class CarwashParser(ResponseParser):
    """Multi-strategy parser for Carwash Paradox responses."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value="other",
                raw_response=response or "",
                parse_strategy="empty",
                confidence=0.0,
                error="Empty response",
            )

        text = response.strip()

        # --- Strategy 1: LaTeX boxed ---
        boxed = re.search(r"\\boxed\{([^}]+)\}", text, re.IGNORECASE)
        if boxed:
            result = _score(boxed.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # --- Strategy 2: Bold / header formatting ---
        bold = re.search(r"\*\*([^*]{1,50})\*\*", text)
        if bold:
            result = _score(bold.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="bold", confidence=0.9)

        # --- Strategy 3: Labelled answer line ---
        label_match = re.search(
            r"(?:answer|recommendation|decision|verdict|conclusion|my\s+(?:advice|recommendation))\s*[:：]\s*([^\n.]{1,120})",
            text,
            re.IGNORECASE,
        )
        if label_match:
            result = _score(label_match.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="label_line", confidence=0.88)

        # --- Strategy 4: First sentence / strong recommendation phrasing ---
        strong_intro = re.search(
            r"(?:you\s+should|i\s+(?:would|recommend|suggest)|definitely|clearly|obviously|"
            r"the\s+(?:answer|best\s+option|right\s+choice)\s+is|go\s+(?:ahead\s+and)?)\s+([^\n.]{1,80})",
            text,
            re.IGNORECASE,
        )
        if strong_intro:
            result = _score(strong_intro.group(0))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="strong_intro", confidence=0.85)

        # --- Strategy 5: Full-text keyword scan ---
        result = _score(text)
        if result:
            return ParsedAnswer(value=result, raw_response=text, parse_strategy="full_text", confidence=0.7)

        # --- Strategy 6: First 3 sentences ---
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sent in sentences[:3]:
            result = _score(sent)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="first_sentences", confidence=0.6)

        # --- Fallback ---
        return ParsedAnswer(
            value="other",
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.1,
            error="Could not extract drive/walk signal",
        )
