---
name: add-plugin
description: Add a new benchmark task plugin to the GoL Benchmark suite. Use when the user asks to "add a new plugin", "create a new benchmark task", "add a new task type", or scaffolds a new directory under src/plugins/. Walks through the auto-discoverable plugin structure (generator + parser + evaluator), the end-first parsing convention, and the multilingual prompt template layout.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Add a New Benchmark Plugin

Plugins in this repo are self-contained directories under `src/plugins/`. The `PluginRegistry` ([src/plugins/__init__.py](../../../src/plugins/__init__.py)) auto-discovers them at runtime by importing each subdirectory and looking for a module-level `plugin` variable. There is **no central registration step** — drop the directory in and it's live.

A complete plugin has 5 files:

```
src/plugins/<task>/
├── __init__.py          # plugin = MyTaskPlugin()
├── prompts.py           # USER_PROMPT_TEMPLATES (nested dict: lang → style → template)
├── generator.py         # generates TestCase objects + ConfigField schema
├── parser.py            # extracts answers from LLM responses (END-FIRST)
└── evaluator.py         # scores correctness, returns EvaluationResult
```

Larger plugins typically also have:
- `i18n.py` or `<task>_i18n.py` — multilingual vocabulary, question templates, scenario narratives
- `data/` — per-language word lists, dataset shards
- `README.md` — short plugin overview (recommended for non-trivial plugins)

---

## Step 1 — Create the directory and `__init__.py`

```bash
mkdir -p src/plugins/<task>/data
```

```python
# src/plugins/<task>/__init__.py
"""<Task Name> Benchmark Plugin — one-line description."""

from src.plugins.base import (
    BenchmarkPlugin,
    ResponseParser,
    ResultEvaluator,
    TestCaseGenerator,
)

from .evaluator import MyTaskEvaluator
from .generator import MyTaskGenerator
from .parser import MyTaskParser


class MyTaskPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "my_task"

    @property
    def display_name(self) -> str:
        return "My Task — what it tests"

    @property
    def description(self) -> str:
        return "One sentence describing what the task measures."

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return MyTaskGenerator()

    def get_parser(self) -> ResponseParser:
        return MyTaskParser()

    def get_evaluator(self) -> ResultEvaluator:
        return MyTaskEvaluator()


plugin = MyTaskPlugin()  # AUTO-DISCOVERED — required module-level instance
```

---

## Step 2 — Prompt templates (`prompts.py`)

Templates are a nested dict keyed by language code, then by user-style. **Not tuple-keyed** (legacy convention; new plugins must use nested form).

```python
# src/plugins/<task>/prompts.py

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal":    "Solve: {problem}",
        "casual":     "Hi! Can you help me figure out {problem}?",
        "linguistic": "Given the problem {problem}, identify the answer following these rules: …",
    },
    "es": {
        "minimal":    "Resuelve: {problem}",
        "casual":     "¡Hola! ¿Puedes ayudarme con {problem}?",
        "linguistic": "…",
    },
    # ... fr, de, zh, uk
}
```

All 6 languages should be populated. If you only have `en` at first, the base class falls back to English when a missing language is requested — but that defeats the multilingual evaluation, so plan to backfill.

---

## Step 3 — Generator (`generator.py`)

```python
# src/plugins/<task>/generator.py
from typing import Any, Dict, List

from src.plugins.base import (
    ConfigField,
    TestCase,
    TestCaseGenerator,
)
from src.plugins.parse_utils import safe_enum, get_language
from src.core.PromptEngine import Language

from .prompts import USER_PROMPT_TEMPLATES


class MyTaskGenerator(TestCaseGenerator):
    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name="count", label="Number of cases", field_type="number",
                        default=10, min_value=1, max_value=200),
            ConfigField(name="difficulty", label="Difficulty", field_type="select",
                        default="medium", options=["easy", "medium", "hard"]),
        ]

    def generate_batch(self, config: Dict[str, Any], prompt_config: Dict[str, Any],
                       count: int, seed: int) -> List[TestCase]:
        language = safe_enum(Language, prompt_config.get("language", "en"), Language.EN)

        cases = []
        for i in range(count):
            problem = self._make_problem(seed + i, config)
            user, system, full = self._build_prompts(
                USER_PROMPT_TEMPLATES,
                language,
                user_style=prompt_config.get("user_style", "casual"),
                system_style=prompt_config.get("system_style", "analytical"),
                problem=problem,
            )
            cases.append(TestCase(
                test_id=f"my_task_{seed + i}",
                task_type="my_task",
                prompts={"user": user, "system": system, "full": full},
                expected_answer=self._compute_answer(problem),
                task_params={"problem": problem},
                prompt_metadata=prompt_config,  # Critical — language flows here
            ))
        return cases
```

Key things:
- `_build_prompts` is provided by the base class. It looks up the template, resolves the system prompt via `_get_system_prompt` (which handles Prompt Studio resolution), and assembles the full prompt.
- `prompt_metadata=prompt_config` MUST be set — the parser/evaluator use `task_params['language']` later, and `run_testset.py` merges `prompt_metadata` INTO `task_params` before parsing. (See CLAUDE.md invariant #3.)

---

## Step 4 — Parser (`parser.py`) — END-FIRST

This is the part that matters most. **Every parser searches from the END of the response toward the start** because LLMs reason first and answer last. Use `re_search_last`, never `re.search`.

```python
# src/plugins/<task>/parser.py
from typing import Any, Dict

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    re_search_last,
    strip_verification_tail,
    normalize_unicode,
    build_answer_label_re,
    get_language,
)


class MyTaskParser(ResponseParser):
    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        # 1. Empty-response guard (canonical strategy name: "empty")
        text = normalize_unicode(response.strip())
        if not text:
            return ParsedAnswer(value=None, raw_response=response,
                                parse_strategy="empty")

        language = get_language(task_params)

        # 2. High-confidence strategies on RAW text (boxed, bold, JSON, code blocks)
        if (m := re_search_last(r"\\boxed\{([^}]+)\}", text)):
            return ParsedAnswer(value=m.group(1).strip(), raw_response=response,
                                parse_strategy="boxed")

        if (m := re_search_last(r"\*\*([^*]+)\*\*", text)):
            return ParsedAnswer(value=m.group(1).strip(), raw_response=response,
                                parse_strategy="bold")

        # 3. Lower-confidence strategies on STRIPPED text (after verification tail removal)
        stripped = strip_verification_tail(text)
        label_alt = build_answer_label_re(language)
        if (m := re_search_last(rf"(?:{label_alt})\s*[:=]?\s*(\w+)", stripped, flags=...)):
            return ParsedAnswer(value=m.group(1), raw_response=response,
                                parse_strategy="label_line")

        # 4. Final fallback (canonical strategy name: "fallback")
        return ParsedAnswer(value=None, raw_response=response,
                            parse_strategy="fallback")
```

**Conventions to follow** (see `docs/PLUGIN_GUIDE.md § End-First Parsing Convention` for the full spec):

- `parse_strategy="empty"` for empty-response early return; `"fallback"` for end-of-pipeline give-up. Plugin-specific names for everything else. Do not reintroduce legacy names like `"failed"` / `"none"` / `"parse_error"`.
- Apply `normalize_unicode(response.strip())` at parse entry — folds smart quotes + primes to ASCII.
- Apply `strip_verification_tail(text)` ONLY to weaker pattern-scanning strategies; keep high-confidence format strategies (boxed, bold, JSON, code block) on raw text.
- For multilingual answer-label matching, use `build_answer_label_re(lang)` and add a plugin-local `_EXTRA_LABELS` dict if you need domain-specific labels (e.g. `"therefore" / "equals"`).
- Read existing parsers like [src/plugins/carwash/parser.py](../../../src/plugins/carwash/parser.py) or [src/plugins/measure_comparison/parser.py](../../../src/plugins/measure_comparison/parser.py) before writing yours — both demonstrate end-first conventions thoroughly.

---

## Step 5 — Evaluator (`evaluator.py`)

```python
# src/plugins/<task>/evaluator.py
from typing import Any, Dict

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class MyTaskEvaluator(ResultEvaluator):
    def evaluate(self, parsed: ParsedAnswer, expected: Any,
                 task_params: Dict[str, Any]) -> EvaluationResult:
        if parsed.value is None:
            return EvaluationResult(correct=False, match_type="parse_error",
                                    accuracy=0.0)

        # Always check expected_answer_localized for multilingual responses
        localized = task_params.get("expected_answer_localized")
        if localized and parsed.value.strip().lower() == str(localized).strip().lower():
            return EvaluationResult(correct=True, match_type="localized_match",
                                    accuracy=1.0)

        if parsed.value.strip().lower() == str(expected).strip().lower():
            return EvaluationResult(correct=True, match_type="exact",
                                    accuracy=1.0)

        return EvaluationResult(correct=False, match_type="mismatch",
                                accuracy=0.0)
```

---

## Step 6 — Verify auto-discovery

```bash
python3 -c "from src.plugins import PluginRegistry; print(sorted(PluginRegistry.list_task_types()))"
```

`my_task` should appear in the list. If it doesn't:

```bash
python3 -c "from src.plugins import PluginRegistry; PluginRegistry.list_task_types(); print(PluginRegistry._discovery_errors)"
```

This shows import errors (e.g. missing dependency, syntax error) that prevented the plugin from loading.

---

## Step 7 — Add tests

Create `tests/plugins/test_my_task.py`. Patterns to copy from existing tests:

- **Generator determinism** — same seed + same config produces identical test cases
- **Parser strategies** — one test per strategy name, with realistic LLM-style responses
- **End-first behavior** — at minimum one test where an intermediate value precedes the final answer
- **Multilingual coverage** — at least one test per supported language

```bash
pytest tests/plugins/test_my_task.py -v
```

---

## Step 8 — Update docs

After the plugin lands and tests pass:

1. Add a row to the table in [docs/README.md § Benchmark Tasks](../../../docs/README.md#benchmark-tasks-21-plugins).
2. Add a per-plugin reference section to [docs/PLUGIN_GUIDE.md § Plugin Reference](../../../docs/PLUGIN_GUIDE.md#plugin-reference) following the existing entry shape.
3. Bump plugin counts in `docs/README.md` and `docs/PLUGIN_GUIDE.md` headers (registry is canonical).
4. Add a CHANGELOG entry under the next release.

The diet doc set has stub patterns for plugins #20 (`fancy_unicode`) and #21 (`picture_algebra`) — copy that shape if you want a minimal stub first and a full write-up later.

---

## What NOT to do

- **Do not add the plugin to a hardcoded list anywhere.** `_KNOWN_TASK_TYPES` (analyze_results.py) and `_TASK_TYPE_SUFFIXES` (reanalyze.py) derive from `PluginRegistry` at import time. The registry is the SSOT.
- **Do not hand-edit `PromptEngine.SYSTEM_PROMPTS`.** That's the legacy enum surface; system prompts are now versioned via Prompt Studio. The base class's `_get_system_prompt` handles resolution automatically.
- **Do not use `re.search()`.** Use `re_search_last()`. (See CLAUDE.md invariant #2.)
- **Do not skip `prompt_metadata=prompt_config`** in TestCase construction. The parser will default to English keywords on multilingual responses.
- **Do not commit plugins that fail to import.** Run the verification step in Step 6 before pushing.

---

*Reference plugins to read before writing yours:*
- *Simplest end-first pattern: [src/plugins/symbol_arithmetic/parser.py](../../../src/plugins/symbol_arithmetic/parser.py)*
- *Multi-strategy with verification-tail handling: [src/plugins/time_arithmetic/parser.py](../../../src/plugins/time_arithmetic/parser.py)*
- *Dual-keyword filtering with positional matching: [src/plugins/carwash/parser.py](../../../src/plugins/carwash/parser.py)*
- *i18n + grammar resolution: [src/plugins/object_tracking/](../../../src/plugins/object_tracking/)*
