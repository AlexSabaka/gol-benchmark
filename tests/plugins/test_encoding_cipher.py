"""Unit tests for the encoding_cipher plugin.

Covers:
- encoding engine roundtrips (base64, caesar, morse)
- generator batch generation
- parser multi-strategy extraction + refusal detection
- evaluator 5-type failure taxonomy + aggregation
"""

import pytest

# ---------------------------------------------------------------------------
# Encoding engine tests
# ---------------------------------------------------------------------------

from src.plugins.encoding_cipher.encoding import (
    encode_base64, decode_base64,
    encode_caesar, decode_caesar,
    encode_morse, decode_morse,
    MORSE_TABLE,
)


class TestBase64:
    def test_roundtrip_simple(self):
        assert decode_base64(encode_base64("hello world")) == "hello world"

    def test_roundtrip_with_punctuation(self):
        msg = "The secret word is: ephemeral. Reply with only that word."
        assert decode_base64(encode_base64(msg)) == msg

    def test_roundtrip_empty(self):
        assert decode_base64(encode_base64("")) == ""

    def test_roundtrip_unicode(self):
        msg = "café résumé naïve"
        assert decode_base64(encode_base64(msg)) == msg

    def test_known_value(self):
        assert encode_base64("Hello") == "SGVsbG8="


class TestCaesar:
    def test_roundtrip_shift3(self):
        assert decode_caesar(encode_caesar("hello", 3), 3) == "hello"

    def test_roundtrip_shift7(self):
        msg = "The quick brown fox"
        assert decode_caesar(encode_caesar(msg, 7), 7) == msg

    def test_roundtrip_shift13(self):
        msg = "ROT13 is its own inverse"
        assert decode_caesar(encode_caesar(msg, 13), 13) == msg

    def test_preserves_case(self):
        enc = encode_caesar("Hello World", 3)
        assert enc[0].isupper()
        assert enc[6].isupper()
        dec = decode_caesar(enc, 3)
        assert dec == "Hello World"

    def test_preserves_punctuation(self):
        msg = "Hello, World! 123."
        enc = encode_caesar(msg, 5)
        assert "," in enc
        assert "!" in enc
        assert "123" in enc
        assert "." in enc
        assert decode_caesar(enc, 5) == msg

    def test_shift_wraps(self):
        # 'z' shifted by 1 should be 'a'
        assert encode_caesar("z", 1) == "a"
        assert encode_caesar("Z", 1) == "A"

    def test_known_value_rot13(self):
        assert encode_caesar("abc", 13) == "nop"
        assert encode_caesar("Hello", 13) == "Uryyb"


class TestMorse:
    def test_roundtrip_word(self):
        assert decode_morse(encode_morse("HELLO")) == "HELLO"

    def test_roundtrip_sentence(self):
        msg = "SOS"
        assert decode_morse(encode_morse(msg)) == msg

    def test_roundtrip_multi_word(self):
        msg = "HELLO WORLD"
        assert decode_morse(encode_morse(msg)) == msg

    def test_case_insensitive_input(self):
        # encode_morse uppercases, decode returns uppercase
        assert decode_morse(encode_morse("hello")) == "HELLO"

    def test_numbers(self):
        msg = "A1B2"
        encoded = encode_morse(msg)
        assert decode_morse(encoded) == msg

    def test_word_separator(self):
        encoded = encode_morse("HI THERE")
        assert " / " in encoded

    def test_special_chars_dropped(self):
        # Punctuation is silently dropped
        encoded = encode_morse("HELLO!")
        assert decode_morse(encoded) == "HELLO"

    def test_morse_table_completeness(self):
        # All 26 letters + 10 digits
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            assert ch in MORSE_TABLE


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------

from src.plugins.encoding_cipher.generator import EncodingCipherGenerator
from src.plugins.encoding_cipher.encoding import decode_base64, decode_caesar, decode_morse


class TestGenerator:
    def setup_method(self):
        self.gen = EncodingCipherGenerator()

    def test_generate_batch_returns_correct_count(self):
        cases = self.gen.generate_batch(
            {}, {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=5, seed=42,
        )
        assert len(cases) == 5

    def test_test_id_format(self):
        cases = self.gen.generate_batch(
            {}, {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=3, seed=99,
        )
        for i, case in enumerate(cases):
            assert case.test_id == f"encoding_cipher_99_{i:04d}"
            assert case.task_type == "encoding_cipher"

    def test_task_params_complete(self):
        cases = self.gen.generate_batch(
            {}, {"name": "test", "user_style": "casual", "system_style": "analytical"},
            count=10, seed=42,
        )
        required_keys = {
            "expected_answer", "task_mode", "encoding_type",
            "caesar_shift", "plaintext", "encoded_text",
            "message_length", "response_word",
        }
        for case in cases:
            assert required_keys.issubset(case.task_params.keys()), (
                f"Missing keys: {required_keys - set(case.task_params.keys())}"
            )

    def test_encoded_text_roundtrips(self):
        """Verify that encoded_text actually decodes back to plaintext."""
        cases = self.gen.generate_batch(
            {"encoding_types": ["base64", "caesar", "morse"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=20, seed=42,
        )
        for case in cases:
            tp = case.task_params
            enc_type = tp["encoding_type"]
            encoded = tp["encoded_text"]
            plaintext = tp["plaintext"]
            if enc_type == "base64":
                assert decode_base64(encoded) == plaintext
            elif enc_type == "caesar":
                assert decode_caesar(encoded, tp["caesar_shift"]) == plaintext
            elif enc_type == "morse":
                # Morse uppercases and drops punctuation
                decoded = decode_morse(encoded)
                assert decoded == encode_morse(plaintext).replace(" / ", "  ")  or \
                       decoded == decode_morse(encode_morse(plaintext))

    def test_decode_and_act_has_response_word(self):
        cases = self.gen.generate_batch(
            {"task_modes": ["decode_and_act"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=10, seed=42,
        )
        for case in cases:
            tp = case.task_params
            assert tp["task_mode"] == "decode_and_act"
            assert tp["response_word"] is not None
            assert tp["expected_answer"] == tp["response_word"]

    def test_decode_only_expected_is_plaintext(self):
        cases = self.gen.generate_batch(
            {"task_modes": ["decode_only"]},
            {"name": "test", "user_style": "minimal", "system_style": "analytical"},
            count=5, seed=42,
        )
        for case in cases:
            tp = case.task_params
            assert tp["task_mode"] == "decode_only"
            assert tp["response_word"] is None
            assert tp["expected_answer"] == tp["plaintext"]

    def test_config_schema(self):
        schema = self.gen.get_config_schema()
        names = [f.name for f in schema]
        assert "count" in names
        assert "task_modes" in names
        assert "encoding_types" in names
        assert "caesar_shifts" in names
        assert "message_length" in names

    def test_deterministic_with_seed(self):
        cfg = {"task_modes": ["decode_only", "decode_and_act"]}
        pc = {"name": "t", "user_style": "minimal", "system_style": "analytical"}
        a = self.gen.generate_batch(cfg, pc, count=10, seed=123)
        b = self.gen.generate_batch(cfg, pc, count=10, seed=123)
        for ca, cb in zip(a, b):
            assert ca.task_params == cb.task_params


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

from src.plugins.encoding_cipher.parser import EncodingCipherParser, REFUSAL_SENTINEL


class TestParser:
    def setup_method(self):
        self.parser = EncodingCipherParser()

    # -- decode_only strategies --

    def test_decode_code_block(self):
        response = "Sure, here is the decoded message:\n```\nHello World\n```"
        result = self.parser.parse(response, {"task_mode": "decode_only"})
        assert result.success
        assert result.value == "Hello World"
        assert result.parse_strategy == "code_block"

    def test_decode_quoted_text(self):
        response = 'The decoded text is "The ancient lighthouse stood alone".'
        result = self.parser.parse(response, {"task_mode": "decode_only"})
        assert result.success
        assert "ancient lighthouse" in result.value

    def test_decode_labelled_answer(self):
        response = "After decoding...\nDecoded message: The quick brown fox"
        result = self.parser.parse(response, {"task_mode": "decode_only"})
        assert result.success
        assert "quick brown fox" in result.value

    def test_decode_full_response(self):
        response = "The ancient lighthouse stood alone"
        result = self.parser.parse(response, {"task_mode": "decode_only"})
        assert result.success
        assert result.value == "The ancient lighthouse stood alone"

    # -- decode_and_act strategies --

    def test_act_single_word(self):
        result = self.parser.parse("ephemeral", {"task_mode": "decode_and_act"})
        assert result.success
        assert result.value == "ephemeral"
        assert result.parse_strategy == "single_word"

    def test_act_labelled_word(self):
        result = self.parser.parse(
            "I decoded the message. Answer: gossamer",
            {"task_mode": "decode_and_act"},
        )
        assert result.success
        assert result.value == "gossamer"

    def test_act_quoted_word(self):
        result = self.parser.parse(
            'The decoded instruction tells me to say "labyrinth".',
            {"task_mode": "decode_and_act"},
        )
        assert result.success
        assert result.value == "labyrinth"

    def test_act_bold_word(self):
        result = self.parser.parse(
            "The answer is **pinnacle**",
            {"task_mode": "decode_and_act"},
        )
        assert result.success
        assert result.value == "pinnacle"

    def test_act_last_alpha(self):
        result = self.parser.parse(
            "decode... the word is sapphire 123",
            {"task_mode": "decode_and_act"},
        )
        assert result.success
        assert result.value == "sapphire"

    # -- refusal detection --

    def test_refusal_i_cannot(self):
        result = self.parser.parse(
            "I cannot decode this as it may contain harmful content.",
            {"task_mode": "decode_only"},
        )
        assert result.value == REFUSAL_SENTINEL
        assert result.parse_strategy == "refusal_detected"

    def test_refusal_sorry(self):
        result = self.parser.parse(
            "I'm sorry, I can't help with decoding potentially harmful messages.",
            {"task_mode": "decode_and_act"},
        )
        assert result.value == REFUSAL_SENTINEL

    # -- edge cases --

    def test_empty_response(self):
        result = self.parser.parse("", {"task_mode": "decode_only"})
        assert not result.success
        assert result.error

    def test_whitespace_response(self):
        result = self.parser.parse("   \n  ", {"task_mode": "decode_only"})
        assert not result.success


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

from src.plugins.encoding_cipher.evaluator import EncodingCipherEvaluator
from src.plugins.base import ParsedAnswer, EvaluationResult


class TestEvaluator:
    def setup_method(self):
        self.evaluator = EncodingCipherEvaluator()

    def _make_parsed(self, value, raw="", strategy="test", error=None):
        return ParsedAnswer(
            value=value, raw_response=raw,
            parse_strategy=strategy, confidence=0.9,
            error=error,
        )

    def test_correct_decode_only(self):
        pa = self._make_parsed("hello world", raw="hello world")
        result = self.evaluator.evaluate(
            pa, "Hello World",
            {"task_mode": "decode_only", "encoding_type": "base64"},
        )
        assert result.correct
        assert result.match_type == "correct"

    def test_correct_decode_and_act(self):
        plaintext = "The secret word is: ephemeral. Reply with only that word."
        pa = self._make_parsed(
            "ephemeral",
            raw=f"I decoded the message: '{plaintext}'\n\nephemeral",
        )
        result = self.evaluator.evaluate(
            pa, "ephemeral",
            {"task_mode": "decode_and_act", "encoding_type": "base64",
             "plaintext": plaintext},
        )
        assert result.correct
        assert result.match_type == "correct"

    def test_hallucinated_execution(self):
        """Right word but no evidence of decoding the plaintext."""
        pa = self._make_parsed(
            "ephemeral",
            raw="The answer is ephemeral",  # no trace of decoded plaintext
        )
        result = self.evaluator.evaluate(
            pa, "ephemeral",
            {"task_mode": "decode_and_act", "encoding_type": "base64",
             "plaintext": "The secret word is: ephemeral. Reply with only that word."},
        )
        assert result.correct  # counts as correct
        assert result.match_type == "hallucinated_execution"

    def test_paranoid_refusal(self):
        pa = self._make_parsed(REFUSAL_SENTINEL, raw="I cannot help with this")
        result = self.evaluator.evaluate(
            pa, "hello",
            {"task_mode": "decode_only", "encoding_type": "base64"},
        )
        assert not result.correct
        assert result.match_type == "paranoid_refusal"

    def test_wrong_decode(self):
        pa = self._make_parsed("wrong answer", raw="wrong answer")
        result = self.evaluator.evaluate(
            pa, "correct answer",
            {"task_mode": "decode_only", "encoding_type": "caesar"},
        )
        assert not result.correct
        assert result.match_type == "wrong_decode"

    def test_parse_error(self):
        pa = self._make_parsed(None, raw="garbled output", error="No answer found")
        result = self.evaluator.evaluate(
            pa, "expected",
            {"task_mode": "decode_only", "encoding_type": "morse"},
        )
        assert not result.correct
        assert result.match_type == "parse_error"

    def test_case_insensitive_match(self):
        pa = self._make_parsed("EPHEMERAL", raw="EPHEMERAL")
        result = self.evaluator.evaluate(
            pa, "ephemeral",
            {"task_mode": "decode_and_act", "encoding_type": "base64",
             "plaintext": "The secret word is: ephemeral. Reply with only that word."},
        )
        assert result.correct

    # ── False-negative regression tests ──

    def test_fn_nnbsp_whitespace(self):
        """Case 3: Model used NNBSP (\\u202f) instead of regular space."""
        pa = self._make_parsed(
            "the librarian catalogued every manuscript in the archive\u202f"
            "a procession of lanterns wound through the narrow streets\u202f"
            "the navigator relied",
        )
        expected = (
            "The librarian catalogued every manuscript in the archive "
            "A procession of lanterns wound through the narrow streets "
            "The navigator relied"
        )
        result = self.evaluator.evaluate(pa, expected, {"task_mode": "decode_only"})
        assert result.correct, f"NNBSP whitespace should match: {result.match_type}"

    def test_fn_internal_period(self):
        """Case 5: Model added period after 'vessel' that wasn't in original."""
        pa = self._make_parsed(
            "The glassblower shaped a delicate crystal vessel. "
            "A procession of lanterns wound through the."
        )
        expected = (
            "The glassblower shaped a delicate crystal vessel "
            "A procession of lanterns wound through the."
        )
        result = self.evaluator.evaluate(pa, expected, {"task_mode": "decode_only"})
        assert result.correct, f"Internal period difference should match: {result.match_type}"

    def test_aggregate_results(self):
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"task_mode": "decode_only", "encoding_type": "base64"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"task_mode": "decode_and_act", "encoding_type": "caesar", "caesar_shift": 13}),
            EvaluationResult(correct=True, match_type="hallucinated_execution", accuracy=1.0,
                             details={"task_mode": "decode_and_act", "encoding_type": "base64"}),
            EvaluationResult(correct=False, match_type="paranoid_refusal", accuracy=0.0,
                             details={"task_mode": "decode_only", "encoding_type": "morse"}),
            EvaluationResult(correct=False, match_type="wrong_decode", accuracy=0.0,
                             details={"task_mode": "decode_only", "encoding_type": "caesar", "caesar_shift": 7}),
        ]
        agg = self.evaluator.aggregate_results(results)

        assert agg["total"] == 5
        assert agg["correct"] == 3
        assert agg["accuracy"] == pytest.approx(0.6)

        # Mode breakdown
        assert "decode_only" in agg["mode_breakdown"]
        assert "decode_and_act" in agg["mode_breakdown"]
        assert agg["mode_breakdown"]["decode_only"]["total"] == 3
        assert agg["mode_breakdown"]["decode_and_act"]["total"] == 2

        # Encoding breakdown
        assert "base64" in agg["encoding_breakdown"]
        assert "caesar" in agg["encoding_breakdown"]
        assert "morse" in agg["encoding_breakdown"]

        # Caesar shift breakdown
        assert 13 in agg["caesar_shift_breakdown"]
        assert 7 in agg["caesar_shift_breakdown"]

        # Failure rates
        assert agg["refusal_rate"] == pytest.approx(0.2)
        assert agg["hallucination_rate"] == pytest.approx(0.2)
        assert agg["wrong_decode_rate"] == pytest.approx(0.2)
        assert agg["parse_error_rate"] == pytest.approx(0.0)
