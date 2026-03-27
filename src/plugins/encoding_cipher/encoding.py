"""Encoding/decoding engine for Base64, Caesar cipher, and Morse code.

Pure-function module — all functions are deterministic with no randomness.
"""

import base64
import string

# ---------------------------------------------------------------------------
# Morse code — ITU international standard
# ---------------------------------------------------------------------------

MORSE_TABLE = {
    "A": ".-",    "B": "-...",  "C": "-.-.",  "D": "-..",
    "E": ".",     "F": "..-.",  "G": "--.",   "H": "....",
    "I": "..",    "J": ".---",  "K": "-.-",   "L": ".-..",
    "M": "--",    "N": "-.",    "O": "---",   "P": ".--.",
    "Q": "--.-",  "R": ".-.",   "S": "...",   "T": "-",
    "U": "..-",   "V": "...-",  "W": ".--",   "X": "-..-",
    "Y": "-.--",  "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}

_MORSE_REVERSE = {v: k for k, v in MORSE_TABLE.items()}


# ---------------------------------------------------------------------------
# Base64
# ---------------------------------------------------------------------------

def encode_base64(plaintext: str) -> str:
    """Encode plaintext to Base64 string."""
    return base64.b64encode(plaintext.encode("utf-8")).decode("ascii")


def decode_base64(encoded: str) -> str:
    """Decode a Base64 string back to plaintext."""
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")


# ---------------------------------------------------------------------------
# Caesar / ROT-N cipher
# ---------------------------------------------------------------------------

def _shift_char(ch: str, shift: int) -> str:
    """Shift a single letter by *shift* positions, preserving case."""
    if ch in string.ascii_lowercase:
        return chr((ord(ch) - ord("a") + shift) % 26 + ord("a"))
    if ch in string.ascii_uppercase:
        return chr((ord(ch) - ord("A") + shift) % 26 + ord("A"))
    return ch  # non-alpha passes through unchanged


def encode_caesar(plaintext: str, shift: int) -> str:
    """Apply Caesar cipher with the given shift. Preserves case, spaces, punctuation."""
    return "".join(_shift_char(ch, shift) for ch in plaintext)


def decode_caesar(encoded: str, shift: int) -> str:
    """Reverse a Caesar cipher by shifting in the opposite direction."""
    return encode_caesar(encoded, -shift)


# ---------------------------------------------------------------------------
# Morse code
# ---------------------------------------------------------------------------

def encode_morse(plaintext: str) -> str:
    """Encode plaintext to Morse code.

    Letters are separated by a single space; words by `` / ``.
    Non-alphanumeric characters (except spaces) are silently dropped.
    """
    words = plaintext.upper().split()
    coded_words = []
    for word in words:
        codes = [MORSE_TABLE[ch] for ch in word if ch in MORSE_TABLE]
        if codes:
            coded_words.append(" ".join(codes))
    return " / ".join(coded_words)


def decode_morse(encoded: str) -> str:
    """Decode Morse code back to plaintext (uppercase).

    Expects letters separated by single space and words by `` / ``.
    """
    words = encoded.split(" / ")
    decoded_words = []
    for word in words:
        chars = [_MORSE_REVERSE.get(code, "") for code in word.split()]
        decoded_words.append("".join(chars))
    return " ".join(decoded_words)
