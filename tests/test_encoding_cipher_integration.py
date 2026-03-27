"""Integration tests for the encoding_cipher plugin.

Verifies:
- Plugin auto-discovery via PluginRegistry
- End-to-end generate → parse → evaluate pipeline
- Config schema well-formedness
"""

import pytest

from src.plugins import PluginRegistry
from src.plugins.base import ConfigField


class TestPluginDiscovery:
    def test_registry_finds_plugin(self):
        plugin = PluginRegistry.get("encoding_cipher")
        assert plugin is not None

    def test_task_type(self):
        plugin = PluginRegistry.get("encoding_cipher")
        assert plugin.task_type == "encoding_cipher"

    def test_display_name(self):
        plugin = PluginRegistry.get("encoding_cipher")
        assert "Encoding" in plugin.display_name

    def test_listed_in_all_plugins(self):
        all_types = PluginRegistry.list_task_types()
        assert "encoding_cipher" in all_types

    def test_components_instantiate(self):
        plugin = PluginRegistry.get("encoding_cipher")
        gen = plugin.get_generator()
        parser = plugin.get_parser()
        evaluator = plugin.get_evaluator()
        assert gen is not None
        assert parser is not None
        assert evaluator is not None


class TestConfigSchema:
    def test_schema_returns_config_fields(self):
        plugin = PluginRegistry.get("encoding_cipher")
        schema = plugin.get_generator().get_config_schema()
        assert all(isinstance(f, ConfigField) for f in schema)

    def test_schema_has_required_fields(self):
        plugin = PluginRegistry.get("encoding_cipher")
        schema = plugin.get_generator().get_config_schema()
        names = {f.name for f in schema}
        assert {"count", "task_modes", "encoding_types", "caesar_shifts", "message_length"}.issubset(names)

    def test_schema_serializes(self):
        plugin = PluginRegistry.get("encoding_cipher")
        schema = plugin.get_generator().get_config_schema()
        for f in schema:
            d = f.to_dict()
            assert "name" in d
            assert "type" in d  # ConfigField.to_dict() uses "type", not "field_type"


class TestEndToEnd:
    """Full pipeline: generate → parse mock response → evaluate."""

    def setup_method(self):
        plugin = PluginRegistry.get("encoding_cipher")
        self.generator = plugin.get_generator()
        self.parser = plugin.get_parser()
        self.evaluator = plugin.get_evaluator()

    def test_decode_only_correct(self):
        cases = self.generator.generate_batch(
            {"task_modes": ["decode_only"], "encoding_types": ["base64"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=1, seed=42,
        )
        case = cases[0]
        plaintext = case.task_params["plaintext"]

        # Simulate a model that returns the correct plaintext
        parsed = self.parser.parse(f'The decoded message is: "{plaintext}"', case.task_params)
        assert parsed.success

        result = self.evaluator.evaluate(parsed, case.task_params["expected_answer"], case.task_params)
        assert result.correct
        assert result.match_type == "correct"

    def test_decode_and_act_correct(self):
        cases = self.generator.generate_batch(
            {"task_modes": ["decode_and_act"], "encoding_types": ["caesar"]},
            {"name": "test", "user_style": "casual", "system_style": "analytical"},
            count=1, seed=42,
        )
        case = cases[0]
        word = case.task_params["response_word"]
        plaintext = case.task_params["plaintext"]

        # Simulate model that decoded and responded with just the word
        parsed = self.parser.parse(
            f"I decoded the message. It says: '{plaintext}'\n\n{word}",
            case.task_params,
        )
        assert parsed.success

        result = self.evaluator.evaluate(parsed, case.task_params["expected_answer"], case.task_params)
        assert result.correct

    def test_decode_and_act_hallucinated(self):
        cases = self.generator.generate_batch(
            {"task_modes": ["decode_and_act"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=1, seed=42,
        )
        case = cases[0]
        word = case.task_params["response_word"]

        # Model gives the right word but shows no decoding work
        parsed = self.parser.parse(word, case.task_params)
        assert parsed.success

        result = self.evaluator.evaluate(parsed, case.task_params["expected_answer"], case.task_params)
        assert result.correct
        assert result.match_type == "hallucinated_execution"

    def test_refusal_pipeline(self):
        cases = self.generator.generate_batch(
            {},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=1, seed=42,
        )
        case = cases[0]

        parsed = self.parser.parse(
            "I'm sorry, I can't decode this message as it might contain harmful content.",
            case.task_params,
        )
        result = self.evaluator.evaluate(parsed, case.task_params["expected_answer"], case.task_params)
        assert not result.correct
        assert result.match_type == "paranoid_refusal"

    def test_wrong_answer_pipeline(self):
        cases = self.generator.generate_batch(
            {"task_modes": ["decode_only"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=1, seed=42,
        )
        case = cases[0]

        parsed = self.parser.parse("totally wrong text that does not match", case.task_params)
        result = self.evaluator.evaluate(parsed, case.task_params["expected_answer"], case.task_params)
        assert not result.correct
        assert result.match_type == "wrong_decode"

    def test_all_encoding_types_generate(self):
        """Each encoding type produces valid test cases."""
        for enc in ["base64", "caesar", "morse"]:
            cases = self.generator.generate_batch(
                {"encoding_types": [enc], "task_modes": ["decode_only"]},
                {"name": "test", "user_style": "minimal", "system_style": "analytical"},
                count=3, seed=42,
            )
            assert len(cases) == 3
            for case in cases:
                assert case.task_params["encoding_type"] == enc
                assert case.task_params["encoded_text"]
                assert case.task_params["plaintext"]

    def test_aggregate_across_modes(self):
        """Generate mixed cases, evaluate them, and check aggregation."""
        cases = self.generator.generate_batch(
            {"task_modes": ["decode_only", "decode_and_act"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=10, seed=42,
        )
        results = []
        for case in cases:
            # Simulate always-correct model for decode_only, wrong for decode_and_act
            tp = case.task_params
            if tp["task_mode"] == "decode_only":
                response = f'"{tp["plaintext"]}"'
            else:
                response = "wrong word"

            parsed = self.parser.parse(response, tp)
            result = self.evaluator.evaluate(parsed, tp["expected_answer"], tp)
            results.append(result)

        agg = self.evaluator.aggregate_results(results)
        assert agg["total"] == 10
        assert "mode_breakdown" in agg
        assert "encoding_breakdown" in agg
