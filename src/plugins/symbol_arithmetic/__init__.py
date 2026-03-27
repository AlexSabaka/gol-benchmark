"""
Symbol Arithmetic Benchmark Plugin

Tests LLM ability to evaluate expressions under completely arbitrary
binary operations defined by an inline lookup table, with no mathematical
semantics to fall back on.  Exposes simulation failure when models assume
commutativity, associativity, or identity elements that the defined
operation does not have.
"""

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.symbol_arithmetic.generator import SymbolArithmeticGenerator
from src.plugins.symbol_arithmetic.parser import SymbolArithmeticParser
from src.plugins.symbol_arithmetic.evaluator import SymbolArithmeticEvaluator


class SymbolArithmeticPlugin(BenchmarkPlugin):

    @property
    def task_type(self) -> str:
        return "symbol_arithmetic"

    @property
    def display_name(self) -> str:
        return "Symbol Arithmetic"

    @property
    def description(self) -> str:
        return (
            "Custom operation tables on abstract symbol sets — pure "
            "rule-following with zero semantic anchor.  Detects when "
            "models incorrectly assume commutativity or associativity."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return SymbolArithmeticGenerator()

    def get_parser(self) -> ResponseParser:
        return SymbolArithmeticParser()

    def get_evaluator(self) -> ResultEvaluator:
        return SymbolArithmeticEvaluator()


plugin = SymbolArithmeticPlugin()
