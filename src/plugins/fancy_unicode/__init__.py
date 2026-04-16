"""fancy_unicode plugin — Unicode normalization benchmark.

Tests LLM ability to recognize and decode decorative Unicode encodings
(math-script fonts, small caps, fullwidth, enclosed alphanumerics,
superscript/subscript) and follow instructions embedded in the decoded text.

Unlike encoding_cipher (which explicitly labels the encoding type), this
plugin presents decorated text as-is — the model must identify the style
on its own.  This surfaces failure modes specific to each Unicode family
and reveals world-knowledge bypass behaviors.

Supports 12 encoding families in 3 tiers:
  Tier 1 — full A–Z a–z (math_script_bold, math_italic, math_monospace, fullwidth)
  Tier 2 — partial coverage (small_caps, superscript, subscript, circled)
  Tier 3 — uppercase only / combining (squared, negative_squared,
            negative_circled, dotted_script)

Languages: EN only (Unicode decoration is language-agnostic at the codepoint
level; multilingual extension is possible but non-trivial).
"""

from src.plugins.base import BenchmarkPlugin

from .evaluator import FancyUnicodeEvaluator
from .generator import FancyUnicodeGenerator
from .parser import FancyUnicodeParser


class FancyUnicodePlugin(BenchmarkPlugin):
    """Benchmark plugin for decorative Unicode normalization."""

    @property
    def task_type(self) -> str:
        return "fancy_unicode"

    @property
    def display_name(self) -> str:
        return "Fancy Unicode Normalization"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> FancyUnicodeGenerator:
        return FancyUnicodeGenerator()

    def get_parser(self) -> FancyUnicodeParser:
        return FancyUnicodeParser()

    def get_evaluator(self) -> FancyUnicodeEvaluator:
        return FancyUnicodeEvaluator()


plugin = FancyUnicodePlugin()
