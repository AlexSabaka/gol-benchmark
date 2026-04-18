"""Emoji pools for picture_algebra surface forms.

Each pool is a flat list of single-grapheme emoji (no ZWJ sequences — those
can trip up models that tokenize on codepoints rather than grapheme clusters).
``MIXED`` unions all three topical pools and is the default when broad
semantic interference is desired.
"""
from __future__ import annotations

from typing import Dict, List

FOOD: List[str] = [
    "🍎", "🍌", "🍊", "🍇", "🍓", "🍍", "🍉", "🍒",
    "🥝", "🥑", "🥕", "🌽", "🥦", "🧀", "🍞", "🥐",
    "🍔", "🍕", "🌭", "🍟", "🍩", "🍪", "🍰", "🍫",
]

ANIMALS: List[str] = [
    "🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🐨",
    "🐯", "🦁", "🐸", "🐵", "🐔", "🐧", "🦆", "🦉",
    "🐺", "🐗", "🐴", "🦓", "🦒", "🐘", "🦏", "🐢",
]

OBJECTS: List[str] = [
    "🎁", "📚", "⚽", "🎸", "🎨", "🔑", "💡", "⌚",
    "📷", "🔨", "🎹", "🎺", "🎯", "🎳", "⚓", "🚲",
    "⛵", "🎈", "🧸", "🎂", "🔔", "⏰", "🧭", "🪁",
]

MIXED: List[str] = FOOD + ANIMALS + OBJECTS

EMOJI_POOLS: Dict[str, List[str]] = {
    "food": FOOD,
    "animals": ANIMALS,
    "objects": OBJECTS,
    "mixed": MIXED,
}
