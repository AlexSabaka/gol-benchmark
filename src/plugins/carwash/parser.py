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
from src.plugins.parse_utils import (
    re_search_last, last_sentences,
    merge_keywords, merge_patterns, build_answer_label_re, get_language,
)

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

DRIVE_KEYWORDS = {
    "en": [
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
    ],
    "es": [
        r"\bconducir\b", r"\bmanejar\b", r"\bir en (?:coche|auto|carro)\b",
        r"\btomar (?:el|tu|mi) (?:coche|auto|carro)\b",
        r"\busar (?:el|tu|mi) (?:coche|auto|carro)\b",
        r"\bve en (?:coche|auto)\b",
    ],
    "fr": [
        r"\bconduire\b", r"\bprendre (?:la|ta|ma) voiture\b",
        r"\butler en voiture\b", r"\by aller en voiture\b",
        r"\butiliser (?:la|ta|ma) voiture\b",
    ],
    "de": [
        r"\bfahren\b", r"\bAuto (?:nehmen|benutzen)\b",
        r"\bmit dem Auto\b", r"\bhin ?fahren\b",
    ],
    "zh": [
        "开车", "驾车", "坐车", "用车", "开.*去",
    ],
    "ua": [
        r"\bїхати\b", r"\bпоїхати\b", r"\bвзяти (?:машину|авто)\b",
        r"\bсісти за кермо\b", r"\bна (?:машині|авто)\b",
    ],
}

WALK_KEYWORDS = {
    "en": [
        r"\bwalk\b",
        r"\bwalking\b",
        r"\bon\s+foot\b",
        r"\bfoot\b",
        r"\bstroll\b",
        r"\bpedestrian\b",
    ],
    "es": [r"\bcaminar\b", r"\bir a pie\b", r"\bpeatonal\b", r"\bpasear\b"],
    "fr": [r"\bmarcher\b", r"\bà pied\b", r"\bpiéton\b", r"\bse promener\b"],
    "de": [r"\blaufen\b", r"\bzu Fuß\b", r"\bgehen\b", r"\bFußgänger\b"],
    "zh": ["走路", "步行", "走着去", "徒步"],
    "ua": [r"\bйти пішки\b", r"\bпішки\b", r"\bпішохідний\b", r"\bпрогулятися\b"],
}

# Negative tokens that flip a "walk" match (e.g. "don't walk")
WALK_NEGATION = {
    "en": [re.compile(
        r"\b(don'?t|do not|shouldn'?t|should not|no need to|not necessary to)\s+walk\b",
        re.IGNORECASE,
    )],
    "es": [re.compile(r"(?:no\s+(?:debería|necesita|tiene que)\s+)caminar|ir a pie", re.IGNORECASE)],
    "fr": [re.compile(r"(?:ne\s+(?:devrait|faut|doit)\s+pas\s+)marcher|aller à pied", re.IGNORECASE)],
    "de": [re.compile(r"(?:(?:sollte|muss|braucht)\s+nicht\s+)(?:laufen|zu Fuß gehen)", re.IGNORECASE)],
    "zh": [re.compile(r"不(?:需要|应该|必须)走路|步行")],
    "ua": [re.compile(r"(?:не\s+(?:потрібно|слід|треба)\s+)(?:йти пішки|ходити)", re.IGNORECASE)],
}

# Negative tokens that flip a "drive" match (e.g. "don't drive")
DRIVE_NEGATION = {
    "en": [re.compile(
        r"\b(don'?t|do not|shouldn'?t|should not|no need to|not necessary to)\s+drive\b",
        re.IGNORECASE,
    )],
    "es": [re.compile(r"(?:no\s+(?:debería|necesita|tiene que)\s+)conducir|manejar", re.IGNORECASE)],
    "fr": [re.compile(r"(?:ne\s+(?:devrait|faut|doit)\s+pas\s+)conduire", re.IGNORECASE)],
    "de": [re.compile(r"(?:(?:sollte|muss|braucht)\s+nicht\s+)fahren", re.IGNORECASE)],
    "zh": [re.compile(r"不(?:需要|应该|必须)开车|驾车")],
    "ua": [re.compile(r"(?:не\s+(?:потрібно|слід|треба)\s+)(?:їхати|поїхати)", re.IGNORECASE)],
}


# Conditional / exception language that makes a walk mention non-conclusive

# Pattern A: conditional keyword BEFORE walk (within 80 chars)
# e.g. "exception: ... walk", "if ... you could walk", "the only reason ... walk"
_PRE_WALK_CONDITIONAL = {
    "en": re.compile(
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
    ),
    "es": re.compile(
        r"(?:excepto\s+(?:si|cuando)|la\s+única\s+excepción|alternativamente|"
        r"sin\s+embargo,?\s+si|solo\s+(?:si|cuando))"
        r".{0,80}?\b(?:caminar|a pie|peatonal)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "fr": re.compile(
        r"(?:sauf\s+(?:si|quand)|la\s+seule\s+exception|alternativement|"
        r"cependant,?\s+si|seulement\s+(?:si|quand))"
        r".{0,80}?\b(?:marcher|à pied|piéton)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "de": re.compile(
        r"(?:außer\s+(?:wenn|falls)|die\s+einzige\s+Ausnahme|alternativ|"
        r"jedoch,?\s+wenn|nur\s+(?:wenn|falls))"
        r".{0,80}?\b(?:laufen|zu Fuß|gehen)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "zh": re.compile(
        r"(?:除非|例外|只有.*?(?:情况|时候)|如果)"
        r".{0,40}?(?:走路|步行|徒步)",
        re.DOTALL,
    ),
    "ua": re.compile(
        r"(?:за винятком|єдиний виняток|альтернативно|"
        r"однак,?\s+якщо|тільки\s+(?:якщо|коли))"
        r".{0,80}?\b(?:пішки|ходити|йти пішки)\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

# Pattern B: "only walk" or walk immediately followed by conditional
# e.g. "only walk if ...", "walk if ...", "walk only when ..."
_WALK_CONDITIONAL = {
    "en": re.compile(
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
    ),
    "es": re.compile(
        r"\bsolo\s+caminar\b"
        r"|\bcaminar\s+(?:si|solo\s+si|cuando|a menos que)\b"
        r"|\bsi\s+(?:prefieres?|quieres?|decides?)\b.{0,30}?\bcaminar\b"
        r"|\bpodría\s+caminar\b.{0,40}?\bpero\b"
        r"|\bcaminar\b.{0,30}?\bpero\s+(?:tú|eso|el|la|esto)\b"
        r"|\bcaminar\s+en\s+(?:su\s+)?lugar\b",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"\bseulement\s+marcher\b"
        r"|\bmarcher\s+(?:si|seulement\s+si|quand|à moins que)\b"
        r"|\bsi\s+(?:vous\s+)?(?:préférez|voulez|décidez)\b.{0,30}?\bmarcher\b"
        r"|\bpourrait\s+marcher\b.{0,40}?\bmais\b"
        r"|\bmarcher\b.{0,30}?\bmais\s+(?:vous|ça|il|elle|ce)\b"
        r"|\bmarcher\s+(?:à la place|plutôt)\b",
        re.IGNORECASE,
    ),
    "de": re.compile(
        r"\bnur\s+(?:laufen|gehen)\b"
        r"|\b(?:laufen|gehen)\s+(?:wenn|nur\s+wenn|falls|es sei denn)\b"
        r"|\bwenn\s+(?:Sie|du)\s+(?:lieber|möchtest?|willst)\b.{0,30}?\b(?:laufen|gehen)\b"
        r"|\bkönnte\s+(?:laufen|gehen)\b.{0,40}?\baber\b"
        r"|\b(?:laufen|gehen)\b.{0,30}?\baber\s+(?:du|es|das|die|der)\b"
        r"|\b(?:laufen|gehen)\s+stattdessen\b",
        re.IGNORECASE,
    ),
    "zh": re.compile(
        r"只(?:能|有).*?(?:走路|步行)"
        r"|(?:走路|步行).*?(?:如果|只有|除非)"
        r"|如果.*?(?:愿意|想要|选择).*?(?:走路|步行)"
        r"|可以走路.*?但",
    ),
    "ua": re.compile(
        r"\bтільки\s+(?:йти пішки|ходити)\b"
        r"|\b(?:пішки|ходити)\s+(?:якщо|тільки\s+якщо|коли|хіба що)\b"
        r"|\bякщо\s+(?:ви\s+)?(?:хочете|бажаєте|вирішите)\b.{0,30}?\b(?:пішки|ходити)\b"
        r"|\bміг би\s+(?:піти пішки|ходити)\b.{0,40}?\bале\b"
        r"|\b(?:пішки|ходити)\b.{0,30}?\bале\s+(?:ви|це|той|та)\b"
        r"|\b(?:піти пішки|ходити)\s+замість\b",
        re.IGNORECASE,
    ),
}

# Pattern C: walk mentioned in a negative / dismissive context
# e.g. "walking won't", "walking would complicate", "walking leaves your car"
_WALK_NEGATIVE = {
    "en": re.compile(
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
    ),
    "es": re.compile(
        r"\bcaminar\s+(?:\w+\s+)?(?:no\s+(?:va|funcionará|sirve|puede))"
        r"|\bcaminar\s+(?:\w+\s+)?(?:complicaría|sería\s+\w+|dejaría)"
        r"|\bcaminar\s+(?:está|parece)\s+(?:bien|ok)\s*,?\s*pero"
        r"|\bcaminar\s+(?:de\s+)?regreso\b",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"\bmarcher\s+(?:\w+\s+)?(?:ne\s+(?:va|fonctionnera|peut)\s+pas)"
        r"|\bmarcher\s+(?:\w+\s+)?(?:compliquerait|serait\s+\w+|laisserait)"
        r"|\bmarcher\s+(?:est|semble)\s+(?:bien|ok)\s*,?\s*mais"
        r"|\bmarcher\s+(?:en\s+)?retour\b",
        re.IGNORECASE,
    ),
    "de": re.compile(
        r"\b(?:laufen|gehen)\s+(?:\w+\s+)?(?:wird\s+nicht|würde\s+nicht|kann\s+nicht)"
        r"|\b(?:laufen|gehen)\s+(?:\w+\s+)?würde\s+(?:komplizieren|sein\s+\w+|bedeuten)"
        r"|\b(?:laufen|gehen)\s+(?:ist|scheint)\s+(?:ok|in Ordnung)\s*,?\s*aber"
        r"|\bzurück\s*(?:laufen|gehen)\b",
        re.IGNORECASE,
    ),
    "zh": re.compile(
        r"走路.*?(?:不行|不好|麻烦|不方便|不现实|没用)"
        r"|(?:走路|步行).*?但是"
        r"|走回去",
    ),
    "ua": re.compile(
        r"\b(?:піти пішки|ходити)\s+(?:\w+\s+)?(?:не\s+(?:буде|може|вийде))"
        r"|\b(?:піти пішки|ходити)\s+(?:\w+\s+)?(?:ускладнить|буде\s+\w+|залишить)"
        r"|\b(?:пішки|ходити)\s+(?:це|здається)\s+(?:добре|нормально)\s*,?\s*але"
        r"|\bйти\s+назад\b",
        re.IGNORECASE,
    ),
}


def _is_conditional_walk(text: str, walk_start: int, lang: str = "en") -> bool:
    """Return True if the walk mention at *walk_start* is inside conditional language."""
    # Check a window around the walk mention
    window_start = max(0, walk_start - 120)
    window_end = min(len(text), walk_start + 80)
    window = text[window_start:window_end]

    # Check EN patterns always, plus target language patterns
    for code in (["en"] if lang == "en" else ["en", lang]):
        pat = _PRE_WALK_CONDITIONAL.get(code)
        if pat and pat.search(window):
            return True
        pat = _WALK_CONDITIONAL.get(code)
        if pat and pat.search(window):
            return True
        pat = _WALK_NEGATIVE.get(code)
        if pat and pat.search(window):
            return True
    return False


def _score(text: str, lang: str = "en") -> Optional[str]:
    """Return 'drive', 'walk', or None based on keyword presence.

    When both keywords are present, the one whose **last** occurrence is later
    in the text wins (end-first principle: the model's final recommendation).
    Conditional walk mentions (e.g. "only walk if ...") are excluded from the
    tie-break so that a trailing disclaimer does not override a clear "drive".
    """
    t = text.lower()
    drive_kws = merge_keywords(DRIVE_KEYWORDS, lang)
    walk_kws = merge_keywords(WALK_KEYWORDS, lang)
    walk_neg = merge_patterns(WALK_NEGATION, lang)
    drive_neg = merge_patterns(DRIVE_NEGATION, lang)

    has_drive = any(re.search(kw, t) for kw in drive_kws)
    has_walk = any(re.search(kw, t) for kw in walk_kws)
    negated_walk = any(p.search(t) for p in walk_neg)
    negated_drive = any(p.search(t) for p in drive_neg)

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
            (m.start() for kw in drive_kws for m in re.finditer(kw, t)),
            default=-1,
        )
        # Collect all walk positions, filtering out conditional mentions
        all_walk_positions = [
            m.start()
            for kw in walk_kws
            for m in re.finditer(kw, t)
        ]
        non_conditional = [
            pos for pos in all_walk_positions
            if not _is_conditional_walk(t, pos, lang)
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
        lang = get_language(task_params or {})

        # --- Strategy 1: LaTeX boxed (last match) ---
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text, re.IGNORECASE)
        if boxed:
            result = _score(boxed.group(1), lang)
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
                r = _score(b.group(1), lang)
                if r == "walk" and _is_conditional_walk(text_lower, b.start(), lang):
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
                result = _score(fragment, lang)
                if result:
                    return ParsedAnswer(value=result, raw_response=text, parse_strategy="first_sentence", confidence=0.88)

        # --- Strategy 4: Labelled answer line (last match) ---
        answer_labels = build_answer_label_re(lang)
        label_match = re_search_last(
            r"(?:" + answer_labels + r"|recommendation|decision|verdict|conclusion|my\s+(?:advice|recommendation))\s*[:：]\s*([^\n.]{1,120})",
            text,
            re.IGNORECASE,
        )
        if label_match:
            result = _score(label_match.group(1), lang)
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
            result = _score(strong_intro.group(0), lang)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="strong_intro", confidence=0.85)

        # --- Strategy 6: Full-text keyword scan ---
        result = _score(text, lang)
        if result:
            return ParsedAnswer(value=result, raw_response=text, parse_strategy="full_text", confidence=0.7)

        # --- Strategy 7: Last 3 sentences (end-first) ---
        for sent in reversed(last_sentences(text, n=5)):
            result = _score(sent, lang)
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
