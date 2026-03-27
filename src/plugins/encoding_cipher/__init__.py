"""Encoding & Cipher Decoding benchmark plugin.

Tests LLM ability to decode Base64, Caesar/ROT-N, and Morse code messages.
Two task modes:
  - decode_only:   Decode and return the plaintext.
  - decode_and_act: Decode an embedded instruction and reply with a single word.
"""

from src.plugins.base import BenchmarkPlugin

from .generator import EncodingCipherGenerator
from .parser import EncodingCipherParser
from .evaluator import EncodingCipherEvaluator


class EncodingCipherPlugin(BenchmarkPlugin):
    """Plugin for encoding/cipher decoding benchmarks."""

    @property
    def task_type(self) -> str:
        return "encoding_cipher"

    @property
    def display_name(self) -> str:
        return "Encoding & Cipher Decoding"

    @property
    def description(self) -> str:
        return (
            "Decode-and-respond tasks across encoding schemes "
            "(Base64, Caesar/ROT-N, Morse code)"
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self):
        return EncodingCipherGenerator()

    def get_parser(self):
        return EncodingCipherParser()

    def get_evaluator(self):
        return EncodingCipherEvaluator()


plugin = EncodingCipherPlugin()
