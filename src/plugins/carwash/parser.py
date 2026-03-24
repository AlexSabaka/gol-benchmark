"""
Carwash Paradox – Response Parser

Extracts the model's answer (drive / walk / other) from free-form text using
multiple strategies, ordered by specificity.

Resolution strategy (all prefer the LAST match — end-first principle):
 1. Explicit boxed answer: \\boxed{drive} / \\boxed{walk}
 2. Bold / header answer: **drive** / **walk**
 3. Keyword "Answer:" / "Recommendation:" / "Decision:" line
 4. Direct keyword search — looks for the last strong signal word
 5. Last sentences that mention drive / walk
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
from src.plugins.parse_utils import re_search_last, last_sentences

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

# Negative tokens that flip a "walk" match (e.g. "don't walk")
WALK_NEGATION = re.compile(
    r"\b(don'?t|do not|shouldn'?t|should not|no need to|not necessary to)\s+walk\b",
    re.IGNORECASE,
)

# Negative tokens that flip a "drive" match (e.g. "don't drive")
DRIVE_NEGATION = re.compile(
    r"\b(don'?t|do not|shouldn'?t|should not|no need to|not necessary to)\s+drive\b",
    re.IGNORECASE,
)


def _score(text: str) -> Optional[str]:
    """Return 'drive', 'walk', or None based on keyword presence.

    When both keywords are present, the one whose **last** occurrence is later
    in the text wins (end-first principle: the model's final recommendation).
    """
    t = text.lower()
    has_drive = any(re.search(kw, t) for kw in DRIVE_KEYWORDS)
    has_walk = any(re.search(kw, t) for kw in WALK_KEYWORDS)
    negated_walk = bool(WALK_NEGATION.search(t))
    negated_drive = bool(DRIVE_NEGATION.search(t))

    # Apply negations
    if has_drive and negated_drive:
        has_drive = False
    if has_walk and negated_walk:
        has_walk = False

    if has_drive and not has_walk:
        return "drive"
    if has_walk and not has_drive:
        return "walk"
    if has_drive and has_walk:
        # Both present — last occurrence wins (end-first principle)
        drive_pos = max(
            (m.start() for kw in DRIVE_KEYWORDS for m in re.finditer(kw, t)),
            default=-1,
        )
        walk_pos = max(
            (m.start() for kw in WALK_KEYWORDS for m in re.finditer(kw, t)),
            default=-1,
        )
        return "drive" if drive_pos > walk_pos else "walk"
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

        # --- Strategy 1: LaTeX boxed (last match) ---
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text, re.IGNORECASE)
        if boxed:
            result = _score(boxed.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # --- Strategy 2: Bold / header formatting (last match) ---
        bold = re_search_last(r"\*\*([^*]{1,50})\*\*", text)
        if bold:
            result = _score(bold.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="bold", confidence=0.9)

        # --- Strategy 3: Labelled answer line (last match) ---
        label_match = re_search_last(
            r"(?:answer|recommendation|decision|verdict|conclusion|my\s+(?:advice|recommendation))\s*[:：]\s*([^\n.]{1,120})",
            text,
            re.IGNORECASE,
        )
        if label_match:
            result = _score(label_match.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="label_line", confidence=0.88)

        # --- Strategy 4: Strong recommendation phrasing (last match) ---
        strong_intro = re_search_last(
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

        # --- Strategy 6: Last 3 sentences (end-first) ---
        for sent in reversed(last_sentences(text, n=5)):
            result = _score(sent)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="last_sentences", confidence=0.6)

        # --- Fallback ---
        return ParsedAnswer(
            value="other",
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.1,
            error="Could not extract drive/walk signal",
        )
