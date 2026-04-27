---
name: add-model-provider
description: Wire up a new LLM provider (e.g. OpenRouter, vLLM, Together, Anthropic, custom HTTP API) to the GoL Benchmark. Use when the user asks to "add support for X provider", "wire up a new LLM API", "integrate provider Y", or starts a new file under src/models/. Walks through the ModelInterface contract, the create_model_interface factory, and the test/discovery integration points.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Add a New Model Provider

The benchmark talks to LLMs through a single interface contract: `ModelInterface.query(prompt, params) → dict`. Adding a new provider means writing one class that satisfies that contract and registering it in the factory.

The three existing providers are reference implementations:

| File | Wire format |
|---|---|
| [src/models/OllamaInterface.py](../../../src/models/OllamaInterface.py) | Ollama REST (urllib-based, no `ollama` package dependency) |
| [src/models/HuggingFaceInterface.py](../../../src/models/HuggingFaceInterface.py) | `transformers` library, local CUDA/MPS/CPU |
| [src/models/OpenAICompatibleInterface.py](../../../src/models/OpenAICompatibleInterface.py) | OpenAI Chat Completions schema (works for vLLM, LM Studio, OpenRouter, Groq, Together) |

**Before writing a new interface**, check whether the new provider is OpenAI-compatible — most modern hosted APIs are. If so, you don't need a new interface at all; pass the provider's `base_url` and `api_key` to the existing `OpenAICompatibleInterface`.

---

## Step 1 — Implement the interface

```python
# src/models/MyProviderInterface.py
"""<Provider Name> wrapper for the benchmark."""

import time
from typing import Any, Dict

from src.models.BaseModelInterface import ModelInterface
from src.utils.logger import get_logger

LOGGER = get_logger(__name__)


class MyProviderInterface(ModelInterface):
    def __init__(self, model_name: str, *, api_key: str = "",
                 base_url: str = "https://api.myprovider.com/v1") -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def query(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Single-turn inference. Must return:
            {
                "response": str,            # the model's text output
                "duration": float,          # wall-clock seconds for the call
                "model_info": dict,         # arbitrary provider metadata
                "tokens_generated": int,    # for was_truncated computation
                "max_tokens_used": int,     # for was_truncated computation
                "finish_reason": str,       # "stop" / "length" / "error" / etc.
            }
        """
        start = time.monotonic()
        try:
            # ... HTTP call, transformers call, whatever ...
            response_text = "..."
            tokens_generated = 123
            finish_reason = "stop"
        except Exception as exc:
            LOGGER.warning("MyProvider query failed: %s", exc)
            return {
                "response": "",
                "duration": time.monotonic() - start,
                "model_info": {"error": str(exc)},
                "tokens_generated": 0,
                "max_tokens_used": params.get("max_tokens", 2048),
                "finish_reason": "error",
            }

        return {
            "response": response_text,
            "duration": time.monotonic() - start,
            "model_info": {"provider": "my_provider", "model": self.model_name},
            "tokens_generated": tokens_generated,
            "max_tokens_used": params.get("max_tokens", 2048),
            "finish_reason": finish_reason,
        }
```

**Required result fields** — these are consumed downstream:

- `response` — the parser sees only this string
- `duration` — analytics charts plot duration distributions
- `model_info` — surfaces in the Jobs UI; include anything useful for debugging
- `tokens_generated`, `max_tokens_used`, `finish_reason` — fed into `output.was_truncated = (finish_reason == "length") or (tokens_generated >= max_tokens_used)`. The `was_truncated` flag drives the auto-toggled `truncated` chip in the human-review UI (Phase 3). If you can't get token counts, return `0` and `params.get("max_tokens", 2048)` — `was_truncated` will simply read False.

**Retry / backoff** — none of the existing interfaces add automatic retry beyond what the underlying SDK does. Retry policy belongs in the caller, not the interface.

---

## Step 2 — Register in the factory

In [src/models/\_\_init\_\_.py](../../../src/models/__init__.py), add an `elif` branch to `create_model_interface`:

```python
elif provider == "my_provider":
    return MyProviderInterface(model_name, api_key=api_key,
                               base_url=base_url or "https://api.myprovider.com/v1")
```

Also add the import at the top:

```python
from .MyProviderInterface import MyProviderInterface
```

And extend `__all__` so the symbol re-exports cleanly.

The factory's `provider` argument flows from the CLI flag `--provider` (in `src/stages/run_testset.py`) and from the Web UI's model selection. **No other registration step is needed** — once the factory knows about the provider, the rest of the pipeline is reachable.

---

## Step 3 — Add provider discovery (optional but recommended)

If your provider has a model-listing endpoint (most do), add discovery to `src/utils/model_providers.py` so the Web UI's model picker can populate from it. Look at how `_discover_ollama_models()` works for the pattern — usually 5–15 lines.

If discovery isn't possible (custom on-prem deployment, etc.), just leave the provider out of the discovery layer — users can still type the model name manually in the UI.

---

## Step 4 — Surface in the Web UI model picker (optional)

Frontend integration lives in [frontend/src/components/model-selection/](../../../frontend/src/components/model-selection/). The existing sections are:

- `OllamaSection` — uses `/api/models` Ollama subkey
- `OpenAIEndpointSection` — accepts a `base_url` + `api_key` per-row
- `HuggingFaceSection` — accepts a HF model ID

If your provider matches one of the patterns (OpenAI-compatible? add a saved endpoint preset; Ollama-like? extend the discovery list), do that. Otherwise add a new `MyProviderSection` component following the existing pattern. This is optional — the CLI works without it.

---

## Step 5 — Smoke test the interface

```bash
python3 -c "
from src.models import create_model_interface
iface = create_model_interface('my_provider', 'some-model-id', api_key='...')
print(iface.query('What is 2 + 2?', {'temperature': 0.1, 'max_tokens': 64}))
"
```

The output should match the result-dict shape from Step 1. Common failure modes:

| Symptom | Likely cause |
|---|---|
| `ValueError: Unknown provider` | Factory `elif` branch missing or typo in provider string |
| Returns `response=""` consistently | Provider auth failed or model name wrong; check `model_info.error` |
| `was_truncated` always False even on long outputs | `tokens_generated` not being populated; check provider's response payload |
| Web UI doesn't list the provider's models | Discovery layer not extended (Step 3) — manually entered names still work |

---

## Step 6 — Run a tiny benchmark end-to-end

```bash
# Pick a small testset to keep the smoke test fast
python src/stages/run_testset.py testsets/<small_testset>.json.gz \
    --model some-model-id --provider my_provider \
    --base-url https://api.myprovider.com/v1 \
    --api-key "$MY_PROVIDER_KEY" \
    --output-dir results/smoke/
```

Then verify a result entry has `output.was_truncated`, `output.duration`, `output.tokens_generated`, and the parsed answer.

---

## Step 7 — Document

1. Append a section to [docs/MODEL_PROVIDERS.md](../../../docs/MODEL_PROVIDERS.md) — there's an existing pattern for each provider.
2. If the provider has notable quirks (rate limits, prompt-format differences, special params), document them there.
3. Add a CHANGELOG entry under the next release.

No CLAUDE.md update needed — the agent index doesn't list providers.

---

## What NOT to do

- **Do not subclass an existing interface** (e.g. `OpenAICompatibleInterface`) just to override one method — write a new interface. The interfaces are intentionally flat and small.
- **Do not call the `anthropic` / `openai` / `cohere` SDKs from inside `ModelInterface.query`** unless you genuinely need them. The existing interfaces lean on `urllib` / `requests` to keep `src/models/` dependency-light. Heavy SDK dependencies belong in optional extras.
- **Do not encrypt credentials inside the interface.** Credentials flow in via the factory; encryption-at-rest is handled by `src/web/job_store.py` + `src/web/crypto.py`. The interface receives plaintext at call time.
- **Do not add retry loops in `query()`.** Retry / backoff policy belongs in the orchestration layer (the job runner) so it can be uniform across providers.
