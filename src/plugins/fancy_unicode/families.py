"""Unicode encoding family definitions for the fancy_unicode plugin.

Each family maps ASCII letters (and some digits) to decorative Unicode
codepoints.  Encoding families are grouped into three tiers by coverage:

  Tier 1 — full A–Z a–z, computed via offset arithmetic
  Tier 2 — partial coverage, explicit char maps
  Tier 3 — uppercase A–Z only (uppercases input), offset arithmetic

Unicode offsets verified against PRD character examples.
"""

from __future__ import annotations

import string
import unicodedata
from typing import Dict, FrozenSet, List

# ---------------------------------------------------------------------------
# Tier 1 — offset arithmetic (full alphabet, both cases)
# ---------------------------------------------------------------------------
# Encoding: chr(OFFSET[family][case] + ord(char))
# Verified with PRD examples: e.g. encode_text("strawberry", "math_script_bold")
# == "𝓼𝓽𝓻𝓪𝔀𝓫𝓮𝓻𝓻𝔂"

_TIER1_OFFSETS: Dict[str, Dict[str, int]] = {
    # Mathematical Bold Script (U+1D4D0–U+1D503)
    "math_script_bold": {
        "upper": 0x1D4D0 - ord("A"),   # 𝓐–𝓩
        "lower": 0x1D4EA - ord("a"),   # 𝓪–𝔃
    },
    # Mathematical Sans-Serif Italic (U+1D608–U+1D63B)
    "math_italic": {
        "upper": 0x1D608 - ord("A"),   # 𝘈–𝘡
        "lower": 0x1D622 - ord("a"),   # 𝘢–𝘻
    },
    # Mathematical Monospace (U+1D670–U+1D6A3)
    "math_monospace": {
        "upper": 0x1D670 - ord("A"),   # 𝙰–𝚉
        "lower": 0x1D68A - ord("a"),   # 𝚊–𝚣
    },
    # Halfwidth and Fullwidth Forms (U+FF21–U+FF5A)
    "fullwidth": {
        "upper": 0xFF21 - ord("A"),    # Ａ–Ｚ
        "lower": 0xFF41 - ord("a"),    # ａ–ｚ
    },
}

# Circled alphanumerics (U+24B6–U+24E9) — full A–Z a–z coverage
# Listed in Tier 2 in the PRD but has full alphabetic coverage.
_CIRCLED_OFFSETS: Dict[str, int] = {
    "upper": 0x24B6 - ord("A"),  # Ⓐ–Ⓩ
    "lower": 0x24D0 - ord("a"),  # ⓐ–ⓩ
}

# ---------------------------------------------------------------------------
# Tier 3 — uppercase only, offset arithmetic (U+1F100 supplement block)
# ---------------------------------------------------------------------------

_TIER3_OFFSETS: Dict[str, int] = {
    "squared":          0x1F130 - ord("A"),  # 🄰–🅉
    "negative_squared": 0x1F170 - ord("A"),  # 🅰–🆉
    "negative_circled": 0x1F150 - ord("A"),  # 🅐–🅩
}

# ---------------------------------------------------------------------------
# Tier 2 — explicit maps (partial coverage, lowercase only)
# ---------------------------------------------------------------------------
# Missing letters: pass through as original ASCII character.
# Coverage metadata is derived from these maps — do NOT include fallthrough
# chars here, only the successfully encoded ones.

# Small Capitals — 24/26 letters; missing q, x
_SMALL_CAPS_MAP: Dict[str, str] = {
    "a": "\u1D00", "b": "\u0299", "c": "\u1D04", "d": "\u1D05",
    "e": "\u1D07", "f": "\uA730", "g": "\u0262", "h": "\u029C",
    "i": "\u026A", "j": "\u1D0A", "k": "\u1D0B", "l": "\u029F",
    "m": "\u1D0D", "n": "\u0274", "o": "\u1D0F", "p": "\u1D18",
    "r": "\u0280", "s": "\uA731", "t": "\u1D1B", "u": "\u1D1C",
    "v": "\u1D20", "w": "\u1D21", "y": "\u028F", "z": "\u1D22",
}  # ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘʀꜱᴛᴜᴠᴡʏᴢ

# Superscript Modifier Letters — 21/26 letters; missing c, f, q, x, z
_SUPERSCRIPT_MAP: Dict[str, str] = {
    "a": "\u1D43", "b": "\u1D47", "d": "\u1D48", "e": "\u1D49",
    "g": "\u1D4D", "h": "\u02B0", "i": "\u2071", "j": "\u02B2",
    "k": "\u1D4F", "l": "\u02E1", "m": "\u1D50", "n": "\u207F",
    "o": "\u1D52", "p": "\u1D56", "r": "\u02B3", "s": "\u02E2",
    "t": "\u1D57", "u": "\u1D58", "v": "\u1D5B", "w": "\u02B7",
    "y": "\u02B8",
}  # ᵃᵇᵈᵉᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷʸ

# Subscript — 17/26 letters; missing b, c, d, f, g, q, w, y, z
_SUBSCRIPT_MAP: Dict[str, str] = {
    "a": "\u2090", "e": "\u2091", "h": "\u2095", "i": "\u1D62",
    "j": "\u2C7C", "k": "\u2096", "l": "\u2097", "m": "\u2098",
    "n": "\u2099", "o": "\u2092", "p": "\u209A", "r": "\u1D63",
    "s": "\u209B", "t": "\u209C", "u": "\u1D64", "v": "\u1D65",
    "x": "\u2093",
}  # ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ

# ---------------------------------------------------------------------------
# Coverage metadata
# ---------------------------------------------------------------------------
# frozenset of lowercase letters that this family can encode without fallthrough.
# Used by generators to filter word pools and sentence fragments.
# For uppercase-only families, coverage is the uppercase set.

FAMILY_COVERAGE: Dict[str, FrozenSet[str]] = {
    "math_script_bold": frozenset(string.ascii_lowercase),
    "math_italic":      frozenset(string.ascii_lowercase),
    "math_monospace":   frozenset(string.ascii_lowercase),
    "fullwidth":        frozenset(string.ascii_lowercase),
    "small_caps":       frozenset(_SMALL_CAPS_MAP.keys()),
    "superscript":      frozenset(_SUPERSCRIPT_MAP.keys()),
    "subscript":        frozenset(_SUBSCRIPT_MAP.keys()),
    "circled":          frozenset(string.ascii_lowercase),
    "dotted_script":    frozenset(string.ascii_lowercase),
    # Tier 3: uppercase only — content is uppercased before encoding
    "squared":          frozenset(string.ascii_uppercase),
    "negative_squared": frozenset(string.ascii_uppercase),
    "negative_circled": frozenset(string.ascii_uppercase),
}

# Families that encode uppercase only (input is .upper()'d before encoding)
UPPERCASE_ONLY_FAMILIES: FrozenSet[str] = frozenset({
    "squared", "negative_squared", "negative_circled",
})

# Tier groupings (used for shorthand config values)
TIER1_FAMILIES: List[str] = ["math_script_bold", "math_italic", "math_monospace", "fullwidth"]
TIER2_FAMILIES: List[str] = ["small_caps", "superscript", "subscript", "circled"]
TIER3_FAMILIES: List[str] = ["squared", "negative_squared", "negative_circled", "dotted_script"]
ALL_FAMILIES: List[str] = TIER1_FAMILIES + TIER2_FAMILIES + TIER3_FAMILIES

_TIER_SHORTCUTS: Dict[str, List[str]] = {
    "tier_1": TIER1_FAMILIES,
    "tier_2": TIER2_FAMILIES,
    "tier_3": TIER3_FAMILIES,
    "all":    ALL_FAMILIES,
}

# ---------------------------------------------------------------------------
# Encoding functions
# ---------------------------------------------------------------------------

def _encode_char(char: str, family: str) -> str:
    """Encode a single character using the given family.

    Uppercase/lowercase are preserved for Tier 1 and circled.
    Tier 2 maps are lowercase-only (uppercase chars pass through as-is).
    Tier 3 families only handle uppercase (caller must uppercase first).
    Spaces and non-alpha chars always pass through unchanged.
    """
    if char == " " or not char.isalpha():
        return char

    # --- Tier 1: offset arithmetic ---
    if family in _TIER1_OFFSETS:
        offsets = _TIER1_OFFSETS[family]
        if char.isupper():
            return chr(offsets["upper"] + ord(char))
        else:
            return chr(offsets["lower"] + ord(char))

    # --- Circled: offset arithmetic ---
    if family == "circled":
        if char.isupper():
            return chr(_CIRCLED_OFFSETS["upper"] + ord(char))
        else:
            return chr(_CIRCLED_OFFSETS["lower"] + ord(char))

    # --- Tier 2: explicit dict lookup (lowercase chars only) ---
    if family == "small_caps":
        return _SMALL_CAPS_MAP.get(char.lower(), char)
    if family == "superscript":
        return _SUPERSCRIPT_MAP.get(char.lower(), char)
    if family == "subscript":
        return _SUBSCRIPT_MAP.get(char.lower(), char)

    # --- Tier 3: uppercase only ---
    if family in _TIER3_OFFSETS:
        # Caller is responsible for uppercasing; we only handle A–Z
        if char.isupper():
            return chr(_TIER3_OFFSETS[family] + ord(char))
        return char  # fallthrough for lowercase (should not happen)

    # --- dotted_script: math_script_bold base + combining dot above ---
    if family == "dotted_script":
        base = _encode_char(char, "math_script_bold")
        return base + "\u0307"  # U+0307 COMBINING DOT ABOVE

    return char  # unknown family → passthrough


def encode_text(text: str, family: str) -> str:
    """Encode an entire string using the given family.

    For uppercase-only families (squared, negative_squared, negative_circled),
    the input is uppercased before encoding.  All other characters (spaces,
    digits, punctuation) pass through unchanged.
    """
    if family in UPPERCASE_ONLY_FAMILIES:
        text = text.upper()
    return "".join(_encode_char(c, family) for c in text)


def word_covered_by(word: str, family: str) -> bool:
    """Return True iff every alphabetic character in *word* can be encoded
    without fallthrough for the given family.

    For uppercase-only families, all alpha chars are valid (they get uppercased).
    For dotted_script, coverage is the same as math_script_bold (full).
    """
    if family in UPPERCASE_ONLY_FAMILIES:
        return all(c.isalpha() or not c.isalpha() for c in word)

    coverage = FAMILY_COVERAGE.get(family, frozenset())
    for c in word:
        if c.isalpha() and c.lower() not in coverage:
            return False
    return True


def text_covered_by(text: str, family: str) -> bool:
    """Return True iff every word in *text* is covered by the family."""
    return all(word_covered_by(w, family) for w in text.split())


def get_family_list(config_value: List[str]) -> List[str]:
    """Expand tier shortcuts and return a flat list of family names.

    ``config_value`` may contain a mix of family names and tier shortcuts
    (``"tier_1"``, ``"tier_2"``, ``"tier_3"``, ``"all"``).  Duplicates are
    removed while preserving order.
    """
    seen: set[str] = set()
    result: List[str] = []
    for item in config_value:
        expanded = _TIER_SHORTCUTS.get(item, [item])
        for fam in expanded:
            if fam not in seen and fam in set(ALL_FAMILIES):
                seen.add(fam)
                result.append(fam)
    return result or TIER1_FAMILIES  # safe fallback


# ---------------------------------------------------------------------------
# Reverse map: fancy Unicode → ASCII
# Used by the parser and evaluator to normalise model responses that may
# echo the answer still encoded (e.g. small_caps, negative_squared).
# NFKD alone does not cover small_caps or Tier-3 negative_* families.
# ---------------------------------------------------------------------------

def _build_reverse_map() -> Dict[str, str]:
    """Build a comprehensive fancy-char → lowercase-ASCII lookup.

    Covers all 12 encoding families.  Duplicate codepoints (none expected)
    are silently overwritten — whichever family registers last wins.
    """
    rev: Dict[str, str] = {}

    # Tier 1 — offset arithmetic (both cases map to lowercase ASCII)
    # offset = unicode_start - ord('A'/'a'), so encoded char = chr(offset + ord(ascii))
    for offsets in _TIER1_OFFSETS.values():
        for i, ascii_c in enumerate(string.ascii_uppercase):
            rev[chr(offsets["upper"] + ord("A") + i)] = ascii_c.lower()
        for i, ascii_c in enumerate(string.ascii_lowercase):
            rev[chr(offsets["lower"] + ord("a") + i)] = ascii_c

    # Circled (full A–Z a–z)
    for i, ascii_c in enumerate(string.ascii_uppercase):
        rev[chr(_CIRCLED_OFFSETS["upper"] + ord("A") + i)] = ascii_c.lower()
    for i, ascii_c in enumerate(string.ascii_lowercase):
        rev[chr(_CIRCLED_OFFSETS["lower"] + ord("a") + i)] = ascii_c

    # Tier 2 — invert explicit dicts
    for ascii_c, fancy in _SMALL_CAPS_MAP.items():
        rev[fancy] = ascii_c
    for ascii_c, fancy in _SUPERSCRIPT_MAP.items():
        rev[fancy] = ascii_c
    for ascii_c, fancy in _SUBSCRIPT_MAP.items():
        rev[fancy] = ascii_c

    # Tier 3 — uppercase-only offset arithmetic
    for offset in _TIER3_OFFSETS.values():
        for i, ascii_c in enumerate(string.ascii_uppercase):
            rev[chr(offset + ord("A") + i)] = ascii_c.lower()

    # dotted_script: same base chars as math_script_bold (combining dot
    # U+0307 is not a letter and passes through NFKD stripping fine)
    # — already covered by the math_script_bold entries above.

    return rev


#: Prebuilt reverse lookup used by :func:`decode_to_ascii`.
FANCY_TO_ASCII: Dict[str, str] = _build_reverse_map()


def decode_to_ascii(text: str) -> str:
    """Decode any fancy-Unicode characters in *text* back to plain ASCII.

    Two-pass approach:
      1. Reverse-map lookup (covers all 12 families, including small_caps
         and negative_* families that NFKD does not handle).
      2. NFKD normalization + ASCII stripping for anything not in the map.

    Returns lowercase ASCII.
    """
    mapped = "".join(FANCY_TO_ASCII.get(c, c) for c in text)
    return unicodedata.normalize("NFKD", mapped).encode("ascii", "ignore").decode()
