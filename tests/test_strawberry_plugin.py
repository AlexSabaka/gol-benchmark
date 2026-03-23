"""Unit tests for the Strawberry (Letter Counting) plugin."""
import pytest
from src.plugins import PluginRegistry
from src.plugins.base import ParsedAnswer


@pytest.fixture
def plugin():
    return PluginRegistry.get("strawberry")


@pytest.fixture
def generator(plugin):
    return plugin.get_generator()


@pytest.fixture
def parser(plugin):
    return plugin.get_parser()


@pytest.fixture
def evaluator(plugin):
    return plugin.get_evaluator()


# ── Plugin discovery ─────────────────────────────────────────────

class TestPluginDiscovery:
    def test_registered(self):
        assert "strawberry" in PluginRegistry.list_task_types()

    def test_metadata(self, plugin):
        assert plugin.task_type == "strawberry"
        assert "Letter Counting" in plugin.display_name


# ── Generator ────────────────────────────────────────────────────

class TestGenerator:
    def test_real_mode(self, generator):
        cases = generator.generate_batch(
            config={"mode": "real"},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=1,
        )
        assert len(cases) == 10
        for tc in cases:
            assert tc.task_type == "strawberry"
            assert tc.task_params["mode"] == "real"
            assert tc.task_params["expected_answer"] > 0
            # Verify expected count is correct
            word = tc.task_params["word"]
            letter = tc.task_params["letter"]
            assert word.lower().count(letter.lower()) == tc.task_params["expected_answer"]

    def test_absent_letter_mode(self, generator):
        cases = generator.generate_batch(
            config={"mode": "absent_letter"},
            prompt_config={"user_style": "casual", "system_style": "casual"},
            count=10, seed=2,
        )
        for tc in cases:
            assert tc.task_params["mode"] == "absent_letter"
            assert tc.task_params["expected_answer"] == 0
            assert tc.task_params["letter"] not in tc.task_params["word"]

    def test_random_mode(self, generator):
        cases = generator.generate_batch(
            config={"mode": "random", "random_word_min": 5, "random_word_max": 8},
            prompt_config={"user_style": "linguistic", "system_style": "adversarial"},
            count=10, seed=3,
        )
        for tc in cases:
            assert tc.task_params["mode"] == "random"
            assert 5 <= len(tc.task_params["word"]) <= 8
            assert tc.task_params["word"].isalpha()

    def test_mixed_mode(self, generator):
        cases = generator.generate_batch(
            config={"mode": "mixed"},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=50, seed=4,
        )
        modes = {tc.task_params["mode"] for tc in cases}
        # Mixed should produce at least 2 different modes with 50 cases
        assert len(modes) >= 2

    def test_seed_reproducibility(self, generator):
        cfg = {"mode": "mixed"}
        pc = {"user_style": "minimal", "system_style": "analytical"}
        a = generator.generate_batch(cfg, pc, count=10, seed=99)
        b = generator.generate_batch(cfg, pc, count=10, seed=99)
        for ta, tb in zip(a, b):
            assert ta.task_params["word"] == tb.task_params["word"]
            assert ta.task_params["letter"] == tb.task_params["letter"]

    def test_word_length_filter(self, generator):
        cases = generator.generate_batch(
            config={"mode": "real", "word_lengths": ["short"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=5,
        )
        for tc in cases:
            assert len(tc.task_params["word"]) <= 5

    def test_prompts_structure(self, generator):
        cases = generator.generate_batch(
            config={"mode": "real"},
            prompt_config={"user_style": "casual", "system_style": "adversarial"},
            count=1, seed=6,
        )
        tc = cases[0]
        assert "system" in tc.prompts
        assert "user" in tc.prompts
        assert "full" in tc.prompts
        assert tc.prompts["system"]  # Non-empty
        assert tc.prompts["user"]    # Non-empty

    @pytest.mark.parametrize("lang", ["en", "es", "fr", "de", "zh", "ua"])
    def test_multilingual(self, generator, lang):
        cases = generator.generate_batch(
            config={"mode": "real", "language": lang},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=1, seed=7,
        )
        assert len(cases) == 1
        assert cases[0].prompt_metadata["language"] == lang

    def test_positions_correct(self, generator):
        cases = generator.generate_batch(
            config={"mode": "real"},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=8,
        )
        for tc in cases:
            word = tc.task_params["word"]
            letter = tc.task_params["letter"]
            positions = tc.task_params["letter_positions"]
            # Verify every position is correct
            for pos in positions:
                assert word[pos] == letter
            assert len(positions) == tc.task_params["expected_answer"]


# ── Parser ───────────────────────────────────────────────────────

class TestParser:
    @pytest.mark.parametrize("response,expected", [
        ("3", 3),
        (r"\boxed{2}", 2),
        ("**4**", 4),
        ("The answer is 3.", 3),
        ("Answer: 0", 0),
        ("There are three Rs.", 3),
        ("I think it is five.", 5),
        ("zero", 0),
        ("none", 0),
        ("Count: 7", 7),
        ("Result: 1", 1),
    ])
    def test_parses_correctly(self, parser, response, expected):
        pa = parser.parse(response, {"word_length": 20})
        assert pa.value == expected

    def test_empty_response(self, parser):
        pa = parser.parse("", {})
        assert pa.value is None
        assert pa.error is not None

    def test_unparseable_response(self, parser):
        pa = parser.parse("I really cannot determine that.", {"word_length": 10})
        assert pa.value is None
        assert pa.parse_strategy == "fallback"

    def test_rejects_negative(self, parser):
        pa = parser.parse("-3", {"word_length": 10})
        # Should not return -3
        assert pa.value is None or pa.value >= 0

    def test_confidence_ordering(self, parser):
        """Higher-priority strategies should have higher confidence."""
        boxed = parser.parse(r"\boxed{3}", {"word_length": 10})
        bold = parser.parse("**3**", {"word_length": 10})
        number = parser.parse("blah blah 3", {"word_length": 10})
        assert boxed.confidence > bold.confidence > number.confidence


# ── Evaluator ────────────────────────────────────────────────────

class TestEvaluator:
    def test_correct(self, evaluator):
        pa = ParsedAnswer(value=3, raw_response="3", parse_strategy="boxed", confidence=0.95)
        ev = evaluator.evaluate(pa, 3, {"word": "strawberry", "letter": "r", "mode": "real", "word_length": 10})
        assert ev.correct is True
        assert ev.match_type == "correct"
        assert ev.accuracy == 1.0
        assert ev.details["off_by"] == 0

    def test_wrong(self, evaluator):
        pa = ParsedAnswer(value=5, raw_response="5", parse_strategy="bold", confidence=0.9)
        ev = evaluator.evaluate(pa, 3, {"word": "strawberry", "letter": "r", "mode": "real", "word_length": 10})
        assert ev.correct is False
        assert ev.match_type == "wrong"
        assert ev.details["off_by"] == 2

    def test_parse_error(self, evaluator):
        pa = ParsedAnswer(value=None, raw_response="dunno", parse_strategy="fallback", confidence=0.1, error="no int")
        ev = evaluator.evaluate(pa, 3, {"word": "strawberry", "letter": "r", "mode": "real", "word_length": 10})
        assert ev.correct is False
        assert ev.match_type == "parse_error"

    def test_aggregate(self, evaluator):
        from src.plugins.base import EvaluationResult
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"off_by": 0, "mode": "real"}),
            EvaluationResult(correct=False, match_type="wrong", accuracy=0.0, details={"off_by": 1, "mode": "real"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"off_by": 0, "mode": "absent_letter"}),
        ]
        agg = evaluator.aggregate_results(results)
        assert agg["accuracy"] == pytest.approx(2 / 3)
        assert agg["correct"] == 2
        assert agg["total"] == 3
        assert "real" in agg["mode_breakdown"]
        assert "absent_letter" in agg["mode_breakdown"]
        assert agg["mean_off_by"] == pytest.approx(1 / 3)


# ── Word list ────────────────────────────────────────────────────

class TestWordList:
    def test_loads(self):
        from src.plugins.strawberry.generator import _load_word_list, _TIERS
        buckets = _load_word_list()
        assert set(buckets.keys()) == set(_TIERS.keys())
        total = sum(len(v) for v in buckets.values())
        assert total > 100, f"Expected >100 words, got {total}"

    def test_tier_boundaries(self):
        from src.plugins.strawberry.generator import _load_word_list, _TIERS
        buckets = _load_word_list()
        for tier, words in buckets.items():
            lo, hi = _TIERS[tier]
            for w in words:
                assert lo <= len(w) <= hi, f"Word '{w}' (len={len(w)}) not in {tier} tier [{lo},{hi}]"

    def test_strawberry_present(self):
        from src.plugins.strawberry.generator import _load_word_list
        all_words = sum(_load_word_list().values(), [])
        assert "strawberry" in all_words
