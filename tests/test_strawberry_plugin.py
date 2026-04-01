"""Unit tests for the Strawberry (Character-Level Reasoning) plugin."""
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
        assert "Character Reasoning" in plugin.display_name


# ── Generator (count – backward compatibility) ───────────────────

class TestGeneratorCount:
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
            assert tc.task_params["sub_type"] == "count"
            assert tc.task_params["expected_answer"] > 0
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
        assert tc.prompts["system"]
        assert tc.prompts["user"]

    @pytest.mark.parametrize("lang", ["en", "es", "fr", "de", "zh", "ua"])
    def test_multilingual(self, generator, lang):
        cases = generator.generate_batch(
            config={"mode": "real"},
            prompt_config={"user_style": "minimal", "system_style": "analytical", "language": lang},
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
            for pos in positions:
                assert word[pos] == letter
            assert len(positions) == tc.task_params["expected_answer"]

    def test_default_sub_types_is_count(self, generator):
        """With no sub_types config, only 'count' should be generated."""
        cases = generator.generate_batch(
            config={},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=42,
        )
        for tc in cases:
            assert tc.task_params["sub_type"] == "count"


# ── Generator (reverse) ─────────────────────────────────────────

class TestGeneratorReverse:
    def test_basic(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["reverse"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=10,
        )
        assert len(cases) == 10
        for tc in cases:
            assert tc.task_params["sub_type"] == "reverse"
            word = tc.task_params["word"]
            expected = tc.task_params["expected_answer"]
            assert expected == word[::-1]

    def test_prompt_contains_word(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["reverse"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=1, seed=11,
        )
        word = cases[0].task_params["word"]
        assert word in cases[0].prompts["user"]


# ── Generator (nth_letter) ───────────────────────────────────────

class TestGeneratorNthLetter:
    def test_basic(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["nth_letter"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=20,
        )
        for tc in cases:
            assert tc.task_params["sub_type"] == "nth_letter"
            word = tc.task_params["word"]
            n = tc.task_params["n"]
            assert 1 <= n <= len(word)
            assert tc.task_params["expected_answer"] == word[n - 1]

    def test_seed_reproducibility(self, generator):
        cfg = {"sub_types": ["nth_letter"]}
        pc = {"user_style": "minimal", "system_style": "analytical"}
        a = generator.generate_batch(cfg, pc, count=5, seed=20)
        b = generator.generate_batch(cfg, pc, count=5, seed=20)
        for ta, tb in zip(a, b):
            assert ta.task_params == tb.task_params


# ── Generator (anagram) ─────────────────────────────────────────

class TestGeneratorAnagram:
    def test_basic(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["anagram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=30,
        )
        for tc in cases:
            assert tc.task_params["sub_type"] == "anagram"
            w1 = tc.task_params["word1"]
            w2 = tc.task_params["word2"]
            expected = tc.task_params["expected_answer"]
            is_anagram = sorted(w1.lower()) == sorted(w2.lower())
            assert expected == is_anagram

    def test_has_both_true_and_false(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["anagram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=30, seed=31,
        )
        answers = {tc.task_params["expected_answer"] for tc in cases}
        assert True in answers
        assert False in answers


# ── Generator (pangram) ─────────────────────────────────────────

class TestGeneratorPangram:
    def test_basic(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["pangram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=40,
        )
        for tc in cases:
            assert tc.task_params["sub_type"] == "pangram"
            assert isinstance(tc.task_params["expected_answer"], bool)

    def test_ground_truth_correct(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["pangram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=30, seed=41,
        )
        for tc in cases:
            sentence = tc.task_params["sentence"]
            letters_present = set(ch.lower() for ch in sentence if ch.isalpha())
            is_pangram = letters_present >= set("abcdefghijklmnopqrstuvwxyz")
            assert tc.task_params["expected_answer"] == is_pangram, (
                f"Mismatch for: {sentence!r}"
            )


# ── Generator (lipogram) ────────────────────────────────────────

class TestGeneratorLipogram:
    def test_basic(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["lipogram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=10, seed=50,
        )
        for tc in cases:
            assert tc.task_params["sub_type"] == "lipogram"
            assert isinstance(tc.task_params["expected_answer"], bool)
            assert len(tc.task_params["avoided_letter"]) == 1

    def test_ground_truth_correct(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["lipogram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=30, seed=51,
        )
        for tc in cases:
            sentence = tc.task_params["sentence"]
            avoided = tc.task_params["avoided_letter"]
            actually_avoids = avoided.lower() not in sentence.lower()
            assert tc.task_params["expected_answer"] == actually_avoids, (
                f"Mismatch for avoided='{avoided}' in: {sentence!r}"
            )


# ── Generator (multi sub-type) ──────────────────────────────────

class TestGeneratorMultiSubType:
    def test_all_sub_types(self, generator):
        cases = generator.generate_batch(
            config={"sub_types": ["count", "reverse", "nth_letter", "anagram", "pangram", "lipogram"]},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=60, seed=60,
        )
        sub_types_seen = {tc.task_params["sub_type"] for tc in cases}
        assert sub_types_seen == {"count", "reverse", "nth_letter", "anagram", "pangram", "lipogram"}

    def test_weighted_distribution(self, generator):
        cases = generator.generate_batch(
            config={
                "sub_types": ["count", "reverse"],
                "sub_type_weights": {"count": 0.8, "reverse": 0.2},
            },
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=100, seed=61,
        )
        count_n = sum(1 for tc in cases if tc.task_params["sub_type"] == "count")
        # With 80/20 weights over 100 cases, count should dominate
        assert count_n > 50

    @pytest.mark.parametrize("lang", ["en", "es", "fr", "de", "zh", "ua"])
    def test_multilingual_all_sub_types(self, generator, lang):
        """Each sub-type should generate valid prompts in every language."""
        for st in ["count", "reverse", "nth_letter", "anagram", "pangram", "lipogram"]:
            cases = generator.generate_batch(
                config={"sub_types": [st], "language": lang},
                prompt_config={"user_style": "minimal", "system_style": "analytical"},
                count=1, seed=70,
            )
            assert len(cases) == 1
            assert cases[0].prompts["user"]  # Non-empty prompt


# ── Parser (count – backward compat) ────────────────────────────

class TestParserCount:
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
        assert pa.value is None or pa.value >= 0

    def test_confidence_ordering(self, parser):
        boxed = parser.parse(r"\boxed{3}", {"word_length": 10})
        bold = parser.parse("**3**", {"word_length": 10})
        number = parser.parse("blah blah 3", {"word_length": 10})
        assert boxed.confidence > bold.confidence > number.confidence


# ── Parser (reverse) ────────────────────────────────────────────

class TestParserReverse:
    @pytest.mark.parametrize("response,expected", [
        (r"\boxed{ananab}", "ananab"),
        ("**ananab**", "ananab"),
        ('The reversed word is "ananab".', "ananab"),
        ("Reversed: ananab", "ananab"),
        ("ananab", "ananab"),
    ])
    def test_parses_correctly(self, parser, response, expected):
        pa = parser.parse(response, {"sub_type": "reverse", "word_length": 6})
        assert pa.value is not None
        assert pa.value.lower() == expected.lower()

    def test_rejects_non_alpha(self, parser):
        pa = parser.parse("123456", {"sub_type": "reverse", "word_length": 6})
        # May return None or a value; if value, must be alpha
        if pa.value is not None:
            assert pa.value.isalpha()


# ── Parser (nth_letter) ─────────────────────────────────────────

class TestParserNthLetter:
    @pytest.mark.parametrize("response,expected", [
        (r"\boxed{r}", "r"),
        ("**t**", "t"),
        ("The 3rd letter is 'r'.", "r"),
        ("Answer: r", "r"),
        ("r", "r"),
    ])
    def test_parses_correctly(self, parser, response, expected):
        pa = parser.parse(response, {"sub_type": "nth_letter", "word_length": 10})
        assert pa.value is not None
        assert pa.value.lower() == expected.lower()


# ── Parser (boolean: anagram/pangram/lipogram) ──────────────────

class TestParserBoolean:
    @pytest.mark.parametrize("sub_type", ["anagram", "pangram", "lipogram"])
    @pytest.mark.parametrize("response,expected", [
        (r"\boxed{yes}", True),
        (r"\boxed{no}", False),
        ("**Yes**", True),
        ("**No**", False),
        ("Yes, they are anagrams.", True),
        ("No, this is not a pangram.", False),
        ("The answer is yes.", True),
        ("The answer is no.", False),
        ("True", True),
        ("False", False),
    ])
    def test_parses_correctly(self, parser, sub_type, response, expected):
        pa = parser.parse(response, {"sub_type": sub_type})
        assert pa.value is not None
        assert pa.value == expected

    @pytest.mark.parametrize("sub_type", ["anagram", "pangram", "lipogram"])
    def test_empty_response(self, parser, sub_type):
        pa = parser.parse("", {"sub_type": sub_type})
        assert pa.value is None
        assert pa.error is not None


# ── Evaluator (count – backward compat) ─────────────────────────

class TestEvaluatorCount:
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


# ── Evaluator (reverse) ─────────────────────────────────────────

class TestEvaluatorReverse:
    def test_correct_case_insensitive(self, evaluator):
        pa = ParsedAnswer(value="ANANAB", raw_response="ANANAB", parse_strategy="boxed", confidence=0.95)
        ev = evaluator.evaluate(pa, "ananab", {"sub_type": "reverse", "word": "banana", "word_length": 6})
        assert ev.correct is True

    def test_wrong(self, evaluator):
        pa = ParsedAnswer(value="banana", raw_response="banana", parse_strategy="boxed", confidence=0.95)
        ev = evaluator.evaluate(pa, "ananab", {"sub_type": "reverse", "word": "banana", "word_length": 6})
        assert ev.correct is False
        assert ev.match_type == "wrong"


# ── Evaluator (nth_letter) ──────────────────────────────────────

class TestEvaluatorNthLetter:
    def test_correct(self, evaluator):
        pa = ParsedAnswer(value="r", raw_response="r", parse_strategy="boxed", confidence=0.95)
        ev = evaluator.evaluate(pa, "r", {"sub_type": "nth_letter", "word": "strawberry", "n": 3})
        assert ev.correct is True

    def test_wrong(self, evaluator):
        pa = ParsedAnswer(value="t", raw_response="t", parse_strategy="boxed", confidence=0.95)
        ev = evaluator.evaluate(pa, "r", {"sub_type": "nth_letter", "word": "strawberry", "n": 3})
        assert ev.correct is False


# ── Evaluator (boolean sub-types) ───────────────────────────────

class TestEvaluatorBoolean:
    @pytest.mark.parametrize("sub_type", ["anagram", "pangram", "lipogram"])
    def test_correct_true(self, evaluator, sub_type):
        pa = ParsedAnswer(value=True, raw_response="Yes", parse_strategy="keyword", confidence=0.9)
        ev = evaluator.evaluate(pa, True, {"sub_type": sub_type})
        assert ev.correct is True

    @pytest.mark.parametrize("sub_type", ["anagram", "pangram", "lipogram"])
    def test_correct_false(self, evaluator, sub_type):
        pa = ParsedAnswer(value=False, raw_response="No", parse_strategy="keyword", confidence=0.9)
        ev = evaluator.evaluate(pa, False, {"sub_type": sub_type})
        assert ev.correct is True

    @pytest.mark.parametrize("sub_type", ["anagram", "pangram", "lipogram"])
    def test_wrong(self, evaluator, sub_type):
        pa = ParsedAnswer(value=True, raw_response="Yes", parse_strategy="keyword", confidence=0.9)
        ev = evaluator.evaluate(pa, False, {"sub_type": sub_type})
        assert ev.correct is False
        assert ev.match_type == "wrong"


# ── Evaluator (aggregation) ─────────────────────────────────────

class TestEvaluatorAggregation:
    def test_aggregate_count_only(self, evaluator):
        from src.plugins.base import EvaluationResult
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"off_by": 0, "mode": "real", "sub_type": "count"}),
            EvaluationResult(correct=False, match_type="wrong", accuracy=0.0, details={"off_by": 1, "mode": "real", "sub_type": "count"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"off_by": 0, "mode": "absent_letter", "sub_type": "count"}),
        ]
        agg = evaluator.aggregate_results(results)
        assert agg["accuracy"] == pytest.approx(2 / 3)
        assert agg["correct"] == 2
        assert agg["total"] == 3
        assert "real" in agg["mode_breakdown"]
        assert "absent_letter" in agg["mode_breakdown"]
        assert agg["mean_off_by"] == pytest.approx(1 / 3)

    def test_aggregate_mixed_sub_types(self, evaluator):
        from src.plugins.base import EvaluationResult
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"off_by": 0, "mode": "real", "sub_type": "count"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"sub_type": "reverse"}),
            EvaluationResult(correct=False, match_type="wrong", accuracy=0.0, details={"sub_type": "anagram"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0, details={"sub_type": "pangram"}),
        ]
        agg = evaluator.aggregate_results(results)
        assert agg["accuracy"] == pytest.approx(3 / 4)
        assert "sub_type_breakdown" in agg
        assert agg["sub_type_breakdown"]["count"]["accuracy"] == 1.0
        assert agg["sub_type_breakdown"]["anagram"]["accuracy"] == 0.0
        assert agg["sub_type_breakdown"]["pangram"]["accuracy"] == 1.0
        # mean_off_by only from count sub_type
        assert agg["mean_off_by"] == 0.0


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


# ── Data files ───────────────────────────────────────────────────

class TestDataFiles:
    def test_anagram_pairs_load(self):
        from src.plugins.strawberry.generator import _load_anagram_pairs
        pairs = _load_anagram_pairs()
        assert len(pairs) > 30
        for w1, w2, is_anagram in pairs:
            assert isinstance(w1, str)
            assert isinstance(w2, str)
            assert isinstance(is_anagram, bool)

    def test_anagram_pairs_correct(self):
        from src.plugins.strawberry.generator import _load_anagram_pairs
        for w1, w2, is_anagram in _load_anagram_pairs():
            actual = sorted(w1.lower()) == sorted(w2.lower())
            assert actual == is_anagram, f"Anagram mismatch: {w1},{w2},{is_anagram}"

    def test_pangrams_load(self):
        from src.plugins.strawberry.generator import _load_pangrams
        items = _load_pangrams()
        assert len(items) > 20

    def test_pangrams_correct(self):
        from src.plugins.strawberry.generator import _load_pangrams
        for sentence, is_pangram, missing in _load_pangrams():
            letters = set(ch.lower() for ch in sentence if ch.isalpha())
            actual = letters >= set("abcdefghijklmnopqrstuvwxyz")
            assert actual == is_pangram, f"Pangram mismatch: {sentence!r}"

    def test_lipograms_load(self):
        from src.plugins.strawberry.generator import _load_lipograms
        items = _load_lipograms()
        assert len(items) > 20

    def test_lipograms_correct(self):
        from src.plugins.strawberry.generator import _load_lipograms
        for sentence, avoided, is_lipogram in _load_lipograms():
            actual = avoided.lower() not in sentence.lower()
            assert actual == is_lipogram, f"Lipogram mismatch for '{avoided}': {sentence!r}"
