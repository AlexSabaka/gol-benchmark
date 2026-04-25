"""
Carwash Paradox – Response Parser

Extracts the model's answer (drive / walk / other) from free-form text using
multiple strategies, ordered by specificity.

Resolution strategy (ordered by specificity / signal reliability):
 1. Explicit boxed answer: \\boxed{drive} / \\boxed{walk}
 2. Labelled answer line ("Recommendation:" / "Conclusion:" / "Bottom line:" ...)
 3. Bold — scored across all bolds, conditional-walk filtered
 4. Italic — single-star / underscore emphasis, conditional-walk filtered
 5. First-sentence signal — short opening line with unambiguous answer
 6. Strong recommendation phrasing ("is to …", "would be to …", "you should …")
 7. Full-text keyword scan — end-first with conditional walk filtering
 8. Last sentences that mention drive / walk
 9. Fallback: raw response snippet

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
    has_contextual_marker, normalize_unicode,
)


def _build_label_alternation(lang: str) -> str:
    """Build label alternation for the labelled-answer strategy.

    Combines shared ANSWER_LABELS (via build_answer_label_re) with
    carwash-specific _EXTRA_LABELS (which may contain regex metachars).
    """
    base = build_answer_label_re(lang)
    extra = merge_keywords(_EXTRA_LABELS, lang)
    extra_alt = "|".join(extra) if extra else ""
    if base and extra_alt:
        return base + "|" + extra_alt
    return base or extra_alt

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
        r"\b(?:by|in)\s+(?:a\s+|the\s+)?car\b",                    # "by car", "in the car" (standalone)
        r"\bgo\s+in\s+(?:your|the|my)\s+car\b",
        r"\bget\s+in\s+(?:your|the|my)\s+car\b",
        r"\bcar\b.*\bneed(?:s?)\b",
        r"\bbring\s+(?:your|the|my)\s+car\b",
        r"\btake\s+it\s+there\b",
        r"\bdrive\s+it\s+there\b",
    ],
    "es": [
        r"\bcondu\w+\b",                                          # all conducir forms (conduce, conduces, conducirías, conduciendo...)
        r"\bmaneja\w*\b",                                          # all manejar forms
        r"\bir en (?:coche|auto|carro)\b",
        r"\btomar (?:el|tu|mi) (?:coche|auto|carro)\b",
        r"\busar (?:el|tu|mi) (?:coche|auto|carro)\b",
        r"\bve en (?:coche|auto)\b",
        r"\b(?:en|con)\s+(?:el\s+|un\s+|tu\s+|mi\s+)?(?:coche|auto|carro|vehículo)\b",  # "en coche" standalone too
    ],
    "fr": [
        r"\bconduir\w*\b",                                        # conduir- stem (conduire, conduirais, conduiront...)
        r"\bconduis\w*\b",                                         # conduis- stem (conduisez, conduisons, conduisent, conduisant...)
        r"\bconduite\b",                                            # noun form "la conduite"
        r"\bprendre (?:la|ta|ma) voiture\b",
        r"\baller en voiture\b",
        r"\butiliser (?:la|ta|ma) voiture\b",
        r"\bfaire\s+laver\s+(?:la|ta|ma)\s+voiture\b",            # "get car washed" (implies driving)
        r"\b(?:en|avec)\s+(?:la\s+|ta\s+|ma\s+|une\s+)?voiture\b",  # "en voiture" standalone too
    ],
    "de": [
        # _score uses re.IGNORECASE on raw text — patterns match any case.
        r"\bfahr(?:e|en|t|st)\b",                                  # all present tense: fahre, fahren, fahrt, fahrst
        r"\bfährst\b",                                              # umlaut 2nd person
        r"\bzu\s+fahren\b",                                        # infinitive with zu
        r"\bhinfahren\b", r"\bhin\s*fahren\b",                     # drive there
        r"\b\w*fahren\b",                                           # compound verbs: losfahren, hinfahren, etc.
        r"\bauto\s+(?:nehmen|benutzen|fahren)\b",
        r"\b(?:mit|im|per)\s+(?:dem\s+|einem\s+)?auto\b",          # "mit dem auto" + "im auto" / "per auto"
        r"\b(?:das|zum)\s+fahren\b",                                # nominalized "das fahren"
    ],
    "zh": [
        "开车", "驾车", "坐车", "用车", "开.*去", "开车去", "坐车去",
    ],
    "ua": [
        r"\bїхати\b", r"\bпоїхати\b",                                   # infinitive
        r"\bїдьте\b", r"\bїдь\b", r"\bїдеш\b",                          # imperative / present
        r"\bїхатиме\b", r"\bпоїде\b", r"\bпоїхав\b",                    # future / past
        r"\bвзяти (?:машину|авто|автомобіль)\b",                          # "take the car"
        r"\bсісти за кермо\b",                                            # "get behind the wheel"
        r"(?:на|у|в)\s+(?:машині|авто|автомобілі|автомобілем)\b",        # "by car" (на/у/в machine variants)
        r"\bмашиною\b",                                                   # "by car" (instrumental)
        r"\bпідвез(?:ти|іть|и)\b",                                        # "drive over" / "give a ride"
        r"\bпоїзд(?:ку|кою)\b",                                           # "trip (by car)"
        r"\bтранспорт(?:ом|і)\b",                                         # "by transport"
        r"\bавтомийк[иіу]\b",                                             # "car wash" (implies driving)
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
    "es": [
        r"\bcaminar\b", r"\bcamin[aeo]\w*\b",                     # infinitive + conjugations (camina, camine, caminemos, caminando...)
        r"\bir a pie\b", r"\bpeatonal\b", r"\bpasear\b",
    ],
    "fr": [
        r"\bmarcher\b", r"\bmarche[zs]?\b",                       # infinitive + marche/marches/marchez
        r"\bmarchons\b", r"\bmarchent\b", r"\bmarchant\b",         # 1st plur / 3rd plur / present participle
        r"\bà pied\b", r"\bpiéton\b", r"\bse promener\b",
    ],
    "de": [
        r"\blaufen\b", r"\bzu Fuß\b", r"\bgehen\b", r"\bFußgänger\b",
        r"\bgeh(?:e|st|t)\b",                                     # conjugations: gehe, gehst, geht
        r"\b\w*gehen\b",                                           # compound verbs: losgehen, hingehen, weitergehen
        r"\bfuß\b",                                                # standalone "Fuß" (IGNORECASE)
    ],
    "zh": ["走路", "步行", "走着去", "徒步"],
    "ua": [r"\bйти пішки\b", r"\bпішки\b", r"\bпішохідний\b", r"\bпрогулятися\b"],
}

# Negative tokens that flip a "walk" match (e.g. "don't walk")
WALK_NEGATION = {
    "en": [re.compile(
        r"\b(don'?t|do not|shouldn'?t|should not|no need to|not necessary to)\s+walk\b",
        re.IGNORECASE,
    )],
    "es": [re.compile(r"(?:no\s+(?:debería|necesita|tiene que)\s+)(?:caminar|camin[aeo]\w*|ir a pie)", re.IGNORECASE)],
    "fr": [re.compile(r"(?:ne\s+(?:devrait|faut|doit)\s+pas\s+)(?:marcher|marche[zs]?|aller à pied)", re.IGNORECASE)],
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


# ---------------------------------------------------------------------------
# Label words that precede the final answer (e.g. "Recommendation: Drive")
# Merged with shared ANSWER_LABELS (answer/result/solution/response) at parse
# time via build_answer_label_re(lang). These are plugin-specific additions
# with regex metachars allowed — do not re.escape them.
# ---------------------------------------------------------------------------
_EXTRA_LABELS = {
    "en": [
        "recommendation", "decision", "verdict", "conclusion",
        r"bottom\s*line", r"tl;?dr", r"in\s+short", "tldr",
        r"my\s+(?:advice|recommendation)", r"final\s+answer",
        r"best\s+(?:option|choice)",
    ],
    "es": [
        "recomendación", "decisión", "veredicto", "conclusión",
        r"en\s+resumen", r"en\s+resumidas\s+cuentas",
        r"mi\s+(?:consejo|recomendación)", r"respuesta\s+final",
        r"mejor\s+(?:opción|elección)",
        "resumen",                                                  # standalone summary (context_anchor_groups)
    ],
    "fr": [
        "recommandation", "décision", "verdict", "conclusion",
        r"en\s+résumé", r"en\s+bref",
        r"mon\s+(?:conseil|avis|recommandation)", r"réponse\s+finale",
        r"meilleur(?:e)?\s+(?:option|choix)",
        r"action\s+recommandée",                                    # recommended action (context_anchor_groups)
        "choix",                                                     # standalone choice (context_anchor_groups)
    ],
    "de": [
        "empfehlung", "entscheidung", "urteil", "schlussfolgerung", "fazit",
        r"kurz\s+gesagt", r"mein(?:e)?\s+(?:rat|empfehlung)",
        r"endgültige\s+antwort",
        r"beste\s+(?:option|wahl)",
        "zusammenfassung",                                          # summary (context_anchor_groups)
        "kurzantwort",                                               # short answer (context_anchor_groups)
        "handlungsanleitung",                                       # action instruction (context_anchor_groups)
    ],
    "zh": ["推荐", "建议", "结论", "判断", "最终答案", "总结", "最佳选择", "最好的选择"],
    "ua": [
        "рекомендація", "висновок", "рішення", "вердикт", "підсумок",
        r"коротко\s+кажучи", r"моя\s+(?:порада|рекомендація)",
        r"остаточна\s+відповідь",
        r"найкращий\s+(?:варіант|вибір)",
    ],
}


# ---------------------------------------------------------------------------
# Strong recommendation phrasing that precedes the final answer.
# Each language has one compiled pattern with a capturing group for the
# answer text. Captures are fed through _score() for drive/walk resolution.
# ---------------------------------------------------------------------------
_STRONG_INTRO = {
    "en": re.compile(
        r"(?:you\s+should|i\s+(?:would|recommend|suggest)|definitely|clearly|obviously|"
        r"therefore,?|consequently,?|hence,?|thus,?|"               # conclusion connectors (allow trailing comma)
        r"the\s+(?:answer|best\s+option|right\s+choice|recommended\s+(?:option|action|choice))\s+(?:is|would\s+be)|"
        r"(?:best|optimal|right|recommended)\s+(?:choice|action|option)\s+(?:is|would\s+be)|"
        r"(?:is|would\s+be)\s+to\b|"                               # "is to walk", "would be to drive"
        r"action\s+is\s+to\b|"                                     # "the action is to walk"
        r"go\s+(?:ahead\s+and)?)"
        r"\s+([^\n.]{1,80})",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"(?:deberías|recomiendo|sugiero|claramente|obviamente|"
        r"por\s+lo\s+tanto,?|en\s+consecuencia,?|"                  # conclusion connectors (allow trailing comma)
        r"la\s+(?:respuesta|mejor\s+opción|opción\s+recomendada)\s+es|"
        r"(?:mejor|óptimo|recomendado)\s+(?:es|sería)|"
        r"(?:es|sería)\s+(?:mejor\s+)?)"
        r"\s+([^\n.]{1,80})",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"(?:vous\s+devriez|tu\s+devrais|je\s+recommande|je\s+suggère|définitivement|clairement|évidemment|"
        r"donc,?|par\s+conséquent,?|"                                # conclusion connectors (allow trailing comma)
        r"la\s+(?:réponse|meilleure\s+option|option\s+recommandée)\s+est|"
        r"(?:meilleur|optimal|recommandé)\s+(?:est|serait)|"
        r"(?:est|serait)\s+de)"
        r"\s+([^\n.]{1,80})",
        re.IGNORECASE,
    ),
    "de": re.compile(
        r"(?:du\s+solltest|sie\s+sollten|ich\s+(?:würde|empfehle|schlage\s+vor)|eindeutig|offensichtlich|"
        r"daher,?|deshalb,?|folglich,?|"                             # conclusion connectors (allow trailing comma)
        r"die\s+(?:antwort|beste\s+option|empfohlene\s+option)\s+(?:ist|wäre)|"
        r"(?:beste|optimale|empfohlene)\s+(?:option|wahl)\s+(?:ist|wäre)|"
        r"(?:ist|wäre)\s+zu)"
        r"\s+([^\n.]{1,80})",
        re.IGNORECASE,
    ),
    "zh": re.compile(
        r"(?:你\s*应该|我\s*(?:建议|推荐)|显然|明显|"
        r"(?:答案|最佳选择|推荐选择)\s*(?:是|应该是)|"
        r"建议\s*(?:是|应该))"
        r"\s*([^\n。.]{1,80})",
    ),
    "ua": re.compile(
        r"(?:ви\s+повинні|тобі\s+слід|я\s+(?:рекомендую|раджу)|однозначно|очевидно|"
        r"(?:відповідь|найкращий\s+варіант|рекомендований\s+варіант)\s+(?:це|—|-)|"
        r"(?:це|буде)\s+(?:краще\s+)?)"
        r"\s+([^\n.]{1,80})",
        re.IGNORECASE,
    ),
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
        # "walk or drive" — option listing, not a recommendation
        r"|(?:walk|walking)\s+or\s+(?:driv\w+)"
        # "walk vs drive" / "walk versus drive" — comparison heading
        r"|(?:walk|walking)\s+(?:vs\.?|versus)\s+(?:driv\w+)"
        # "whether to walk" — deliberation framing
        r"|\bwhether\s+to\s+(?:walk|walking)"
        # "determine/decide/choose ... walk" — decision framing
        r"|\b(?:determine|decide|choose)\s+(?:\w+\s+){0,4}(?:walk|walking)"
        r")"
        r".{0,80}?\b(?:walk|walking|on\s+foot)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "es": re.compile(
        r"(?:excepto\s+(?:si|cuando)|la\s+única\s+excepción|alternativamente|"
        r"sin\s+embargo,?\s+si|solo\s+(?:si|cuando)"
        r"|(?:caminar|a pie)\s+o\s+(?:conducir|manejar)"
        r"|(?:caminar|a pie)\s+(?:vs\.?|versus)\s+(?:conducir|manejar)"
        r"|\bsi\s+(?:caminar|ir a pie)"
        r"|\b(?:determinar|decidir|elegir)\s+(?:\w+\s+){0,4}(?:caminar|a pie))"
        r".{0,80}?\b(?:caminar|a pie|peatonal)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "fr": re.compile(
        r"(?:sauf\s+(?:si|quand)|la\s+seule\s+exception|alternativement|"
        r"cependant,?\s+si|seulement\s+(?:si|quand)"
        r"|\bmarcher\s+ou\s+conduire"
        r"|(?:marcher|à pied)\s+(?:vs\.?|versus)\s+(?:conduire|voiture)"
        r"|\bsi\s+(?:marcher|aller à pied)"
        r"|\b(?:déterminer|décider|choisir)\s+(?:\w+\s+){0,4}(?:marcher|à pied))"
        r".{0,80}?\b(?:marcher|à pied|piéton)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "de": re.compile(
        r"(?:außer\s+(?:wenn|falls)|die\s+einzige\s+Ausnahme|alternativ|"
        r"jedoch,?\s+wenn|nur\s+(?:wenn|falls)"
        r"|\b(?:laufen|gehen)\s+oder\s+fahren"
        r"|(?:laufen|gehen|zu Fuß)\s+(?:vs\.?|versus)\s+(?:fahren|auto)"
        r"|\bob\s+(?:man\s+)?(?:laufen|gehen)"
        r"|\b(?:entscheiden|bestimmen|wählen)\s+(?:\w+\s+){0,4}(?:laufen|gehen))"
        r".{0,80}?\b(?:laufen|zu Fuß|gehen)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "zh": re.compile(
        r"(?:除非|例外|只有.*?(?:情况|时候)|如果"
        r"|走路还是开车|步行还是开车"
        r"|(?:决定|选择|确定).*?(?:走路|步行))"
        r".{0,40}?(?:走路|步行|徒步)",
        re.DOTALL,
    ),
    "ua": re.compile(
        r"(?:за винятком|єдиний виняток|альтернативно|"
        r"однак,?\s+якщо|тільки\s+(?:якщо|коли)"
        r"|\b(?:пішки|ходити)\s+чи\s+(?:їхати|поїхати)"
        r"|\bчи\s+(?:йти пішки|ходити)"
        r"|\b(?:визначити|вирішити|обрати)\s+(?:\w+\s+){0,4}(?:пішки|ходити))"
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
        r"|\b(?:walk|walking)\s+instead\b"
        # "drive or walk" — symmetric option listing
        r"|\b(?:drive|driving)\s+or\s+(?:walk|walking)\b"
        # "walk or drive" — walk-first option listing (symmetric counterpart)
        r"|\b(?:walk|walking)\s+(?:or|vs\.?|versus)\s+(?:driv\w+)\b"
        # "drive vs walk" — comparison (symmetric)
        r"|\b(?:drive|driving)\s+(?:vs\.?|versus)\s+(?:walk|walking)\b",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"\bsolo\s+caminar\b"
        r"|\bcaminar\s+(?:si|solo\s+si|cuando|a menos que)\b"
        r"|\bsi\s+(?:prefieres?|quieres?|decides?)\b.{0,30}?\bcaminar\b"
        r"|\bpodría\s+caminar\b.{0,40}?\bpero\b"
        r"|\bcaminar\b.{0,30}?\bpero\s+(?:tú|eso|el|la|esto)\b"
        r"|\bcaminar\s+en\s+(?:su\s+)?lugar\b"
        r"|\b(?:conducir|manejar)\s+o\s+caminar\b"
        r"|\b(?:caminar|a pie)\s+(?:o|vs\.?|versus)\s+(?:conducir|manejar)\b"
        r"|\b(?:conducir|manejar)\s+(?:vs\.?|versus)\s+(?:caminar|a pie)\b",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"\bseulement\s+marcher\b"
        r"|\bmarcher\s+(?:si|seulement\s+si|quand|à moins que)\b"
        r"|\bsi\s+(?:vous\s+)?(?:préférez|voulez|décidez)\b.{0,30}?\bmarcher\b"
        r"|\bpourrait\s+marcher\b.{0,40}?\bmais\b"
        r"|\bmarcher\b.{0,30}?\bmais\s+(?:vous|ça|il|elle|ce)\b"
        r"|\bmarcher\s+(?:à la place|plutôt)\b"
        r"|\b(?:conduire)\s+ou\s+marcher\b"
        r"|\b(?:marcher|à pied)\s+(?:ou|vs\.?|versus)\s+(?:conduire|voiture)\b"
        r"|\b(?:conduire)\s+(?:vs\.?|versus)\s+(?:marcher|à pied)\b",
        re.IGNORECASE,
    ),
    "de": re.compile(
        r"\bnur\s+(?:laufen|gehen)\b"
        r"|\b(?:laufen|gehen)\s+(?:wenn|nur\s+wenn|falls|es sei denn)\b"
        r"|\bwenn\s+(?:Sie|du)\s+(?:lieber|möchtest?|willst)\b.{0,30}?\b(?:laufen|gehen)\b"
        r"|\bkönnte\s+(?:laufen|gehen)\b.{0,40}?\baber\b"
        r"|\b(?:laufen|gehen)\b.{0,30}?\baber\s+(?:du|es|das|die|der)\b"
        r"|\b(?:laufen|gehen)\s+stattdessen\b"
        r"|\bfahren\s+oder\s+(?:laufen|gehen)\b"
        r"|\b(?:laufen|gehen|zu Fuß)\s+(?:oder|vs\.?|versus)\s+(?:fahren|fahr\w+)\b"
        r"|\b(?:fahren)\s+(?:vs\.?|versus)\s+(?:laufen|gehen|zu Fuß)\b",
        re.IGNORECASE,
    ),
    "zh": re.compile(
        r"只(?:能|有).*?(?:走路|步行)"
        r"|(?:走路|步行).*?(?:如果|只有|除非)"
        r"|如果.*?(?:愿意|想要|选择).*?(?:走路|步行)"
        r"|可以走路.*?但"
        r"|开车还是走路|开车或走路",
    ),
    "ua": re.compile(
        r"\bтільки\s+(?:йти пішки|ходити)\b"
        r"|\b(?:пішки|ходити)\s+(?:якщо|тільки\s+якщо|коли|хіба що)\b"
        r"|\bякщо\s+(?:ви\s+)?(?:хочете|бажаєте|вирішите)\b.{0,30}?\b(?:пішки|ходити)\b"
        r"|\bміг би\s+(?:піти пішки|ходити)\b.{0,40}?\bале\b"
        r"|\b(?:пішки|ходити)\b.{0,30}?\bале\s+(?:ви|це|той|та)\b"
        r"|\b(?:піти пішки|ходити)\s+замість\b"
        r"|\b(?:їхати|поїхати)\s+чи\s+(?:йти пішки|ходити)\b",
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
        r"|\b(?:walk|walking)\s+back\b"
        # "walking is faster/cheaper/easier" — explanatory assertion, not recommendation
        r"|\b(?:walk|walking)\s+(?:is|are|would\s+be|seems?)\s+(?:faster|quicker|cheaper|easier|simpler|shorter|more\s+\w+)\b",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"\bcaminar\s+(?:\w+\s+)?(?:no\s+(?:va|funcionará|sirve|puede))"
        r"|\bcaminar\s+(?:\w+\s+)?(?:complicaría|sería\s+\w+|dejaría)"
        r"|\bcaminar\s+(?:está|parece)\s+(?:bien|ok)\s*,?\s*pero"
        r"|\bcaminar\s+(?:de\s+)?regreso\b"
        r"|\bcaminar\s+(?:es|sería)\s+más\s+(?:rápido|barato|fácil|simple|corto)\b",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"\bmarcher\s+(?:\w+\s+)?(?:ne\s+(?:va|fonctionnera|peut)\s+pas)"
        r"|\bmarcher\s+(?:\w+\s+)?(?:compliquerait|serait\s+\w+|laisserait)"
        r"|\bmarcher\s+(?:est|semble)\s+(?:bien|ok)\s*,?\s*mais"
        r"|\bmarcher\s+(?:en\s+)?retour\b"
        r"|\bmarcher\s+(?:est|serait)\s+plus\s+(?:rapide|simple|court)\b",
        re.IGNORECASE,
    ),
    "de": re.compile(
        r"\b(?:laufen|gehen)\s+(?:\w+\s+)?(?:wird\s+nicht|würde\s+nicht|kann\s+nicht)"
        r"|\b(?:laufen|gehen)\s+(?:\w+\s+)?würde\s+(?:komplizieren|sein\s+\w+|bedeuten)"
        r"|\b(?:laufen|gehen)\s+(?:ist|scheint)\s+(?:ok|in Ordnung)\s*,?\s*aber"
        r"|\bzurück\s*(?:laufen|gehen)\b"
        r"|\b(?:laufen|gehen)\s+(?:ist|wäre)\s+(?:schneller|einfacher|billiger|kürzer)\b",
        re.IGNORECASE,
    ),
    "zh": re.compile(
        r"走路.*?(?:不行|不好|麻烦|不方便|不现实|没用)"
        r"|(?:走路|步行).*?但是"
        r"|走回去"
        r"|走路.*?(?:更快|更便宜|更简单|更短)",
    ),
    "ua": re.compile(
        r"\b(?:піти пішки|ходити)\s+(?:\w+\s+)?(?:не\s+(?:буде|може|вийде))"
        r"|\b(?:піти пішки|ходити)\s+(?:\w+\s+)?(?:ускладнить|буде\s+\w+|залишить)"
        r"|\b(?:пішки|ходити)\s+(?:це|здається)\s+(?:добре|нормально)\s*,?\s*але"
        r"|\bйти\s+назад\b"
        r"|\bпішки\s+(?:швидше|дешевше|простіше|коротше)\b",
        re.IGNORECASE,
    ),
}


def _is_conditional_walk(text: str, walk_start: int, lang: str = "en") -> bool:
    """Return True if the walk mention at *walk_start* is inside conditional language."""
    return has_contextual_marker(
        text, walk_start,
        [_PRE_WALK_CONDITIONAL, _WALK_CONDITIONAL, _WALK_NEGATIVE],
        lang, pre_window=120, post_window=80, positional=False,
    )


# ---------------------------------------------------------------------------
# Drive-side option-listing / comparison patterns
# Lighter than walk filtering — only catches option-listing / comparison /
# deliberation framing.  Does NOT filter semantic negation ("driving won't
# help") because dismissive drive language is a genuine walk signal.
# Uses standalone patterns (no trailing anchor) because the window already
# limits proximity — avoids the double-mention issue of the _PRE_WALK style.
# ---------------------------------------------------------------------------
_DRIVE_LISTING = {
    "en": re.compile(
        # "drive or walk" / "drive vs walk" — option listing / comparison
        r"\b(?:drive|driving)\s+(?:or|vs\.?|versus)\s+(?:walk|walking)\b"
        # "walk or drive" — drive is second option in listing
        r"|\b(?:walk|walking)\s+(?:or|vs\.?|versus)\s+(?:driv\w+)\b"
        # "whether to drive" — deliberation framing
        r"|\bwhether\s+to\s+(?:drive|driving)\b"
        # "determine/decide/choose ... drive" — decision framing
        r"|\b(?:determine|decide|choose)\s+(?:\w+\s+){0,4}(?:drive|driving)\b",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"\b(?:conducir|manejar)\s+(?:o|vs\.?|versus)\s+(?:caminar|a pie)\b"
        r"|\b(?:caminar|a pie)\s+(?:o|vs\.?|versus)\s+(?:conducir|manejar)\b"
        r"|\bsi\s+(?:conducir|manejar)\b"
        r"|\b(?:determinar|decidir|elegir)\s+(?:\w+\s+){0,4}(?:conducir|manejar)\b",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"\b(?:conduire)\s+(?:ou|vs\.?|versus)\s+(?:marcher|à pied)\b"
        r"|\b(?:marcher|à pied)\s+(?:ou|vs\.?|versus)\s+(?:conduire|voiture)\b"
        r"|\bsi\s+(?:conduire)\b"
        r"|\b(?:déterminer|décider|choisir)\s+(?:\w+\s+){0,4}(?:conduire)\b",
        re.IGNORECASE,
    ),
    "de": re.compile(
        r"\b(?:fahren)\s+(?:oder|vs\.?|versus)\s+(?:laufen|gehen|zu Fuß)\b"
        r"|\b(?:laufen|gehen|zu Fuß)\s+(?:oder|vs\.?|versus)\s+(?:fahren|auto)\b"
        r"|\bob\s+(?:man\s+)?(?:fahren)\b"
        r"|\b(?:entscheiden|bestimmen|wählen)\s+(?:\w+\s+){0,4}(?:fahren)\b",
        re.IGNORECASE,
    ),
    "zh": re.compile(
        r"开车还是走路|走路还是开车"
        r"|(?:决定|选择|确定).*?(?:开车|驾车)",
    ),
    "ua": re.compile(
        r"\b(?:їхати|поїхати)\s+(?:чи|або)\s+(?:пішки|ходити)\b"
        r"|\b(?:пішки|ходити)\s+(?:чи|або)\s+(?:їхати|поїхати)\b"
        r"|\bчи\s+(?:їхати|поїхати)\b"
        r"|\b(?:визначити|вирішити|обрати)\s+(?:\w+\s+){0,4}(?:їхати|поїхати)\b",
        re.IGNORECASE,
    ),
}


def _is_conditional_drive(text: str, drive_start: int, lang: str = "en") -> bool:
    """Return True if the drive mention at *drive_start* is inside option-listing/comparison language.

    Uses positional matching via ``has_contextual_marker(..., positional=True)``:
    drive_start must fall within the span of a listing-pattern match, not
    merely within the surrounding window.  This avoids false-filtering a
    genuine drive recommendation that happens to sit within 120 chars of
    an earlier option-listing phrase.
    """
    return has_contextual_marker(
        text, drive_start,
        [_DRIVE_LISTING],
        lang, pre_window=120, post_window=80, positional=True,
    )


def _score(text: str, lang: str = "en") -> Optional[str]:
    """Return 'drive', 'walk', or None based on keyword presence.

    When both keywords are present, the one whose **last** occurrence is later
    in the text wins (end-first principle: the model's final recommendation).
    Conditional walk mentions (e.g. "only walk if ...") and option-listing
    drive mentions (e.g. "drive or walk", "drive vs walk") are excluded from
    the tie-break so that framing text does not override the actual answer.
    """
    # Match case-insensitively on the raw text so keyword patterns with
    # capital letters (e.g. German "Auto") work without lowercasing tricks.
    t = text
    drive_kws = merge_keywords(DRIVE_KEYWORDS, lang)
    walk_kws = merge_keywords(WALK_KEYWORDS, lang)
    walk_neg = merge_patterns(WALK_NEGATION, lang)
    drive_neg = merge_patterns(DRIVE_NEGATION, lang)

    has_drive = any(re.search(kw, t, re.IGNORECASE) for kw in drive_kws)
    has_walk = any(re.search(kw, t, re.IGNORECASE) for kw in walk_kws)
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
        # Filter drive positions for option-listing/comparison context
        all_drive_positions = [
            m.start()
            for kw in drive_kws
            for m in re.finditer(kw, t, re.IGNORECASE)
        ]
        non_conditional_drive = [
            pos for pos in all_drive_positions
            if not _is_conditional_drive(t, pos, lang)
        ]
        drive_pos = max(non_conditional_drive, default=-1)

        # Collect all walk positions, filtering out conditional mentions
        all_walk_positions = [
            m.start()
            for kw in walk_kws
            for m in re.finditer(kw, t, re.IGNORECASE)
        ]
        non_conditional = [
            pos for pos in all_walk_positions
            if not _is_conditional_walk(t, pos, lang)
        ]
        walk_pos = max(non_conditional, default=-1)

        # If both filtered to -1 (all mentions are in listings/comparisons),
        # no conclusive signal — let the caller try a different strategy
        if drive_pos == -1 and walk_pos == -1:
            return None

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

        text = normalize_unicode(response.strip())
        lang = get_language(task_params or {})

        # --- Strategy 1: LaTeX boxed (last match) ---
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text, re.IGNORECASE)
        if boxed:
            result = _score(boxed.group(1), lang)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # --- Strategy 2: Labelled answer line (last match) ---
        # Promoted above Bold: "Recommendation: Drive" has 100% regex reliability
        # on the annotated data, whereas bolds fire on explanatory bullets like
        # "**Walking costs basically no fuel**" which mislead the scorer.
        # Bold-aware: handles **Label**: text, **Label**: **text**, **Label: text**
        # by allowing optional \*{0,2} around the label word and after the colon.
        label_alternation = _build_label_alternation(lang)
        label_match = re_search_last(
            r"(?:" + label_alternation + r")(?:\s*\*{0,2})?\s*[:：]\s*(?:\*{0,2}\s*)?([^\n*.]{1,120})",
            text,
            re.IGNORECASE,
        )
        if label_match:
            result = _score(label_match.group(1), lang)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="label_line", confidence=0.9)

        # --- Strategy 2a: Bold-label + bold-answer (no colon separator) ---
        # Covers: **Final Recommendation** **Walk to the carwash**
        #         **Answer:**\n**walk to the carwash**
        # Label must start the bold content (modifier-restricted) to prevent
        # false matches on bolds like **There's no definitive answer**.
        # Optional colon before closing ** handles **Answer:** form.
        _BOLD_LABEL_MODIFIERS = r"(?:(?:final|my|the|best|our)\s+)?"
        bold_label_match = re_search_last(
            r"\*\*" + _BOLD_LABEL_MODIFIERS
            + r"(?:" + label_alternation + r")\s*[:：]?\s*\*\*"
            + r"\s+"
            + r"\*\*\s*([^*\n]{1,80})\s*\*\*",
            text, re.IGNORECASE,
        )
        if bold_label_match:
            result = _score(bold_label_match.group(1), lang)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="bold_label", confidence=0.9)

        # --- Strategy 2b: Label-newline-answer ---
        # Handles label on one line, answer on the next:
        #   ### **Recommendation**\n**Walk to the carwash**
        #   **Best Option**:  \n**Walk**
        #   **Answer:**  \nWalk to the carwash.
        # Optional heading markers (###), optional colon, optional bold wrapping.
        label_newline_match = re_search_last(
            r"(?:#{1,4}\s+)?\*{0,2}\s*(?:" + label_alternation + r")"
            + r"\s*\*{0,2}\s*[:：]?\s*\n"
            + r"\s*\*{0,2}([^\n*.]{1,80})",
            text, re.IGNORECASE,
        )
        if label_newline_match:
            result = _score(label_newline_match.group(1), lang)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="label_newline", confidence=0.88)

        # --- Strategy 3: Bold — score all bolds, filter contextually ---
        # Models bold their answer but also bold explanatory bullet points
        # (e.g. "**Walking back would be awkward**").  For walk-scoring bolds,
        # verify they aren't conditional/negative in the surrounding text.
        # When remaining bolds agree, use the first.  When they conflict
        # (self-correction: "Consider **walking**. Actually no, **drive**.")
        # the last wins.
        # Label-only bolds (e.g. **Recommendation**, **Answer**) are skipped —
        # they are labels, not answer content.
        _label_skip_re = re.compile(
            r"^" + _BOLD_LABEL_MODIFIERS
            + r"(?:" + label_alternation + r")\s*:?\s*$",
            re.IGNORECASE,
        )
        bolds = list(re.finditer(r"\*\*([^*]{1,50})\*\*", text))
        if bolds:
            text_lower = text.lower()
            bold_results = []  # (result, match) pairs
            for b in bolds:
                bold_text = b.group(1).strip()
                if _label_skip_re.match(bold_text):
                    continue  # skip label-only bolds
                r = _score(bold_text, lang)
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

        # --- Strategy 4: Italic — single-star / underscore emphasis ---
        # Models occasionally emphasize the final answer with single-star or
        # underscore italics instead of bold: "...is to *walk*" / "_Walk_".
        # The lookarounds prevent matching inside **bold** runs.
        italics = list(re.finditer(
            r"(?<!\*)\*([^*\n]{1,50})\*(?!\*)|(?<!_)_([^_\n]{1,50})_(?!_)",
            text,
        ))
        if italics:
            text_lower = text.lower()
            italic_results = []
            for m in italics:
                span = (m.group(1) or m.group(2) or "").strip()
                r = _score(span, lang)
                if r == "walk" and _is_conditional_walk(text_lower, m.start(), lang):
                    continue
                if r:
                    italic_results.append((r, m))
            if italic_results:
                signals = {r for r, _ in italic_results}
                result = italic_results[0][0] if len(signals) == 1 else italic_results[-1][0]
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="italic", confidence=0.85)

        # --- Strategy 5: First-sentence signal ---
        # Models sometimes state the answer in the opening line.
        # If a short first line/sentence has an unambiguous signal, trust it.
        first_line = text.split('\n', 1)[0].strip()
        first_sent = re.split(r'[.!?\n]', text, maxsplit=1)[0].strip()
        for fragment in (first_line, first_sent):
            if fragment and len(fragment) < 120:
                result = _score(fragment, lang)
                if result:
                    return ParsedAnswer(value=result, raw_response=text, parse_strategy="first_sentence", confidence=0.88)

        # --- Strategy 6: Strong recommendation phrasing (last match) ---
        strong_intro_pat = _STRONG_INTRO.get(lang) or _STRONG_INTRO["en"]
        strong_intro = re_search_last(strong_intro_pat.pattern, text, strong_intro_pat.flags)
        if strong_intro:
            # Feed the FULL match (intro + tail) through _score so phrases like
            # "the action is to walk" resolve on both the intro and the captured
            # verb. Falls back to capture group if full match is ambiguous.
            result = _score(strong_intro.group(0), lang)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="strong_intro", confidence=0.85)

        # --- Strategy 7: Full-text keyword scan ---
        result = _score(text, lang)
        if result:
            return ParsedAnswer(value=result, raw_response=text, parse_strategy="full_text", confidence=0.7)

        # --- Strategy 8: Last 5 sentences (end-first) ---
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
