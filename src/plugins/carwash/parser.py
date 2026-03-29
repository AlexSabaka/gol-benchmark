"""
Carwash Paradox – Response Parser

Extracts the model's answer (drive / walk / other) from free-form text using
multiple strategies, ordered by specificity.

Resolution strategy:
 1. Explicit boxed answer: \\boxed{drive} / \\boxed{walk}
 2. Bold / header — first bold containing a clear drive/walk signal
 3. First-sentence signal — short opening line with unambiguous answer
 4. Keyword "Answer:" / "Recommendation:" / "Decision:" line (last match)
 5. Strong recommendation phrasing (last match)
 6. Full-text keyword scan — end-first with conditional walk filtering
 7. Last sentences that mention drive / walk
 8. Fallback: raw response snippet

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


# Conditional / exception language that makes a walk mention non-conclusive

# Pattern A: conditional keyword BEFORE walk (within 80 chars)
# e.g. "exception: ... walk", "if ... you could walk", "the only reason ... walk"
_PRE_WALK_CONDITIONAL = re.compile(
    r"(?:"
    # Original patterns
    r"except\s+(?:if|when)\s+|(?:one|the\s+only)\s+exception|alternatively|"
    r"in\s+(?:the\s+)?(?:rare|unlikely|extreme)\s+case|"
    r"however,?\s+if|caveat|disclaimer"
    # "the only time/reason/scenario ... walk"
    r"|(?:the\s+)?only\s+(?:time|reason|scenario|case|situation|argument|way)"
    # "when you might choose/prefer walking"
    r"|when\s+you\s+might"
    # "the main/real argument for walking"
    r"|(?:the\s+)?(?:main|real|primary|sole)\s+(?:argument|reason|case)\s+for"
    # "if any of the above" / "if, for any reason"
    r"|if,?\s+for\s+any\s+reason"
    r"|if\s+any\s+of\s+the\s+above"
    # "if the mud/road/weather" (domain-specific conditionals)
    r"|if\s+the\s+(?:mud|road|weather|plate|visibility)"
    r")"
    r".{0,80}?\b(?:walk|walking|on\s+foot)\b",
    re.IGNORECASE | re.DOTALL,
)

# Pattern B: "only walk" or walk immediately followed by conditional
# e.g. "only walk if ...", "walk if ...", "walk only when ..."
_WALK_CONDITIONAL = re.compile(
    r"\bonly\s+(?:walk|walking)\b"
    r"|\b(?:walk|walking)\s+(?:if|only\s+if|only\s+when|when|unless)\b"
    r"|\b(?:walk|walking)\s+(?:could|might|may)\s+(?:also|be|make)\b"
    # "if you prefer/want/decide to walk"
    r"|\bif\s+you\s+(?:prefer|want|decide|choose|wish|opt|like|rather)\b.{0,30}?\b(?:walk|walking)\b"
    # "could walk ... but" (dismissive concession)
    r"|\bcould\s+(?:walk|walking)\b.{0,40}?\bbut\b"
    # "walk ... but you'd / but it won't / but that" (concession)
    r"|\b(?:walk|walking)\b.{0,30}?\bbut\s+(?:you|it|that|the|this)\b"
    # "walk for exercise" (non-primary motivation)
    r"|\b(?:walk|walking)\s+for\s+(?:exercise|fitness|health|fun)\b"
    # "walk instead" preceded by conditional context (caught via window)
    r"|\b(?:walk|walking)\s+instead\b",
    re.IGNORECASE,
)

# Pattern C: walk mentioned in a negative / dismissive context
# e.g. "walking won't", "walking would complicate", "walking leaves your car"
_WALK_NEGATIVE = re.compile(
    # "walking [there/back] won't / wouldn't / doesn't / can't"
    r"\b(?:walk|walking)\s+(?:\w+\s+)?(?:won'?t|wouldn'?t|doesn'?t|can'?t|cannot|will\s+not|would\s+not|does\s+not)"
    # "walking [there/back] would complicate / be awkward / be silly"
    r"|\b(?:walk|walking)\s+(?:\w+\s+)?would\s+(?:complicate|be\s+\w+|leave|require|mean|take)"
    # "walking [there] leaves your car..."
    r"|\b(?:walk|walking)\s+(?:\w+\s+)?leaves"
    # "walking is fine/okay, but..." (concessive dismissal)
    r"|\b(?:walk|walking)\s+(?:is|seems?)\s+(?:fine|okay|ok)\s*,?\s*but"
    # "walking feels like a chore / silly"
    r"|\b(?:walk|walking)\s+(?:feels?|seems?)\s+(?:like\s+)?(?:a\s+chore|silly|awkward|impractical|pointless)"
    # "walkable but awkward" — not a walk recommendation
    r"|\bwalkable\s+but\b"
    # "walking back" — discussing return trip logistics, not recommending walk
    r"|\b(?:walk|walking)\s+back\b",
    re.IGNORECASE,
)


def _is_conditional_walk(text: str, walk_start: int) -> bool:
    """Return True if the walk mention at *walk_start* is inside conditional language."""
    # Check a window around the walk mention
    window_start = max(0, walk_start - 120)
    window_end = min(len(text), walk_start + 80)
    window = text[window_start:window_end]

    if _PRE_WALK_CONDITIONAL.search(window):
        return True
    if _WALK_CONDITIONAL.search(window):
        return True
    if _WALK_NEGATIVE.search(window):
        return True
    return False


def _score(text: str) -> Optional[str]:
    """Return 'drive', 'walk', or None based on keyword presence.

    When both keywords are present, the one whose **last** occurrence is later
    in the text wins (end-first principle: the model's final recommendation).
    Conditional walk mentions (e.g. "only walk if ...") are excluded from the
    tie-break so that a trailing disclaimer does not override a clear "drive".
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
        # Collect all walk positions, filtering out conditional mentions
        all_walk_positions = [
            m.start()
            for kw in WALK_KEYWORDS
            for m in re.finditer(kw, t)
        ]
        non_conditional = [
            pos for pos in all_walk_positions
            if not _is_conditional_walk(t, pos)
        ]
        walk_pos = max(non_conditional, default=-1)
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

        # --- Strategy 2: Bold — score all bolds, filter contextually ---
        # Models bold their answer but also bold explanatory bullet points
        # (e.g. "**Walking back would be awkward**").  For walk-scoring bolds,
        # verify they aren't conditional/negative in the surrounding text.
        # When remaining bolds agree, use the first.  When they conflict
        # (self-correction: "Consider **walking**. Actually no, **drive**.")
        # the last wins.
        bolds = list(re.finditer(r"\*\*([^*]{1,50})\*\*", text))
        if bolds:
            text_lower = text.lower()
            bold_results = []  # (result, match) pairs
            for b in bolds:
                r = _score(b.group(1))
                if r == "walk" and _is_conditional_walk(text_lower, b.start()):
                    continue  # skip walk bolds in conditional/negative context
                if r:
                    bold_results.append((r, b))
            if bold_results:
                signals = {r for r, _ in bold_results}
                if len(signals) == 1:
                    result = bold_results[0][0]
                else:
                    # Conflict — last bold wins (self-correction)
                    result = bold_results[-1][0]
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="bold", confidence=0.9)

        # --- Strategy 3: First-sentence signal ---
        # Models almost always state the answer in the opening line.
        # If a short first line/sentence has an unambiguous signal, trust it.
        first_line = text.split('\n', 1)[0].strip()
        first_sent = re.split(r'[.!?\n]', text, maxsplit=1)[0].strip()
        for fragment in (first_line, first_sent):
            if fragment and len(fragment) < 120:
                result = _score(fragment)
                if result:
                    return ParsedAnswer(value=result, raw_response=text, parse_strategy="first_sentence", confidence=0.88)

        # --- Strategy 4: Labelled answer line (last match) ---
        label_match = re_search_last(
            r"(?:answer|recommendation|decision|verdict|conclusion|my\s+(?:advice|recommendation))\s*[:：]\s*([^\n.]{1,120})",
            text,
            re.IGNORECASE,
        )
        if label_match:
            result = _score(label_match.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="label_line", confidence=0.88)

        # --- Strategy 5: Strong recommendation phrasing (last match) ---
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

        # --- Strategy 6: Full-text keyword scan ---
        result = _score(text)
        if result:
            return ParsedAnswer(value=result, raw_response=text, parse_strategy="full_text", confidence=0.7)

        # --- Strategy 7: Last 3 sentences (end-first) ---
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
