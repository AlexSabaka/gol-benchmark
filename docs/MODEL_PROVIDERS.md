# Model Providers

**Version 2.26.0** | Last updated: 2026-04-27

The benchmark talks to LLMs through a single contract: `ModelInterface.query(prompt, params) → dict`. Three providers ship today; new ones plug in via the factory in `src/models/__init__.py`. Discovery, grouping, and filtering of *which models a provider exposes* is a separate layer (`src/utils/model_providers.py`) consumed by the Web UI's model picker.

For the full add-a-provider walkthrough, see the [`add-model-provider`](../.claude/skills/add-model-provider/SKILL.md) skill.

---

## The two layers

### Layer 1 — Inference interface (`src/models/`)

Each provider implements `ModelInterface` ([src/models/BaseModelInterface.py](../src/models/BaseModelInterface.py)). The contract is one method:

```python
def query(self, prompt: str, params: dict) -> dict
```

The result dict must include `response`, `duration`, `model_info`, `tokens_generated`, `max_tokens_used`, `finish_reason`. The last three feed `output.was_truncated` (used by the human-review UI's auto-toggle).

| File | Provider | Wire format |
|---|---|---|
| [src/models/OllamaInterface.py](../src/models/OllamaInterface.py) | Ollama | Ollama REST (urllib-based, no `ollama` SDK dependency) |
| [src/models/HuggingFaceInterface.py](../src/models/HuggingFaceInterface.py) | HuggingFace | `transformers` library, local CUDA/MPS/CPU |
| [src/models/OpenAICompatibleInterface.py](../src/models/OpenAICompatibleInterface.py) | OpenAI-compatible | OpenAI Chat Completions schema (works for vLLM, LM Studio, OpenRouter, Groq, Together, …) |

The factory at [src/models/\_\_init\_\_.py](../src/models/__init__.py) selects the right interface from a provider string:

```python
from src.models import create_model_interface

iface = create_model_interface("ollama", "qwen3:0.6b", ollama_host="http://localhost:11434")
result = iface.query("What is 2+2?", {"temperature": 0.1, "max_tokens": 64})
print(result["response"], result["duration"])
```

Provider strings: `"ollama"` / `"huggingface"` / `"openai_compatible"`.

### Layer 2 — Model discovery + metadata (`src/utils/model_providers.py`)

Discovery surfaces "what models does this provider currently have available." It's separate from inference because the Web UI needs to populate dropdowns BEFORE any inference call. Currently used by the `/api/models` endpoint and the matrix wizard.

```python
from src.utils.model_providers import ModelProviderManager

mgr = ModelProviderManager()
ollama_models = mgr.list_models_by_provider("ollama")
for m in ollama_models:
    print(m.display_name)  # e.g. "qwen3:0.6b (380 MB) [Q4_K_M]"
```

`ModelInfo` ([src/utils/model_providers.py](../src/utils/model_providers.py)) carries `name`, `size_bytes`, `size_human`, `quantization` (F16 / Q8_0 / Q6_K / Q5_K_M / Q4_K_M / Q2_K / …), `family` (qwen / gemma / llama / acemath / …), and `display_name`.

Discovery adapters ship for Ollama (parses `ollama list`) and HuggingFace (limited). OpenAI-compatible endpoints don't auto-discover — users enter model IDs manually in the Web UI's `OpenAIEndpointSection`.

---

## Provider notes

### Ollama (primary, recommended for local)

```bash
# Local
python src/stages/run_testset.py testsets/<file>.json.gz \
    --model qwen3:0.6b --provider ollama

# Remote daemon
python src/stages/run_testset.py testsets/<file>.json.gz \
    --model qwen3:0.6b --provider ollama \
    --ollama-host http://192.168.1.50:11434
```

- Detects quantization from model tag (e.g. `qwen3:0.6b-q4_K_M`).
- First query for a given model is slow (~3–5 s while Ollama loads weights); subsequent queries are fast.
- Daemon must be running (`ollama serve`).

### HuggingFace / Transformers

Loads weights via the `transformers` package directly. Auto-selects CUDA → MPS → CPU.

```bash
python src/stages/run_testset.py testsets/<file>.json.gz \
    --model microsoft/DialoGPT-medium --provider huggingface
```

Heavier dependency (`torch` + `transformers`); use only when you need a HF-only model not packaged for Ollama.

### OpenAI-compatible

Any endpoint that speaks OpenAI Chat Completions:

```bash
python src/stages/run_testset.py testsets/<file>.json.gz \
    --model llama-3.1-70b-instruct --provider openai_compatible \
    --base-url https://openrouter.ai/api/v1 \
    --api-key "$OPENROUTER_KEY"
```

Confirmed working with OpenRouter, Groq, Together, vLLM (self-hosted), and LM Studio. **Don't subclass this interface for a similar provider** — pass the right `base_url` and use it as-is.

---

## Web UI integration

The matrix wizard's model selection lives under `frontend/src/components/model-selection/`:

- `OllamaSection` — consumes `/api/models?provider=ollama`, lists discovered models with size + quantization badges
- `OpenAIEndpointSection` — multi-row form for `(base_url, api_key, model_id)` triples; saves credentials encrypted via `frontend/src/lib/credential-store.ts` (AES-GCM in browser localStorage)
- `HuggingFaceSection` — accepts a HF model ID

`favorite-models` ([frontend/src/lib/favorite-models.ts](../frontend/src/lib/favorite-models.ts)) namespaces favorites as `provider:modelId` so the same model name doesn't collide across providers.

---

## Credentials at rest

Inference jobs that include API credentials persist them encrypted under `data/jobs/`:

- Encryption: Fernet via [src/web/crypto.py](../src/web/crypto.py)
- Key: `GOL_SECRET_KEY` env var if set, otherwise auto-generated `data/.secret_key` (mode 0600) on first run
- **Back up `data/.secret_key`** alongside `data/jobs/` — losing it makes existing encrypted credentials unrecoverable (jobs still load, credentials decrypt to `""` with a WARNING, user re-enters to resume)

Both files are in `.gitignore`.

---

## Adding a new provider

Quickest path for OpenAI-compatible endpoints (most modern hosted APIs):

> You don't need a new interface. Pass the provider's `base_url` + `api_key` to the existing `OpenAICompatibleInterface`.

For genuinely new wire formats:

1. Implement `ModelInterface` at `src/models/MyProviderInterface.py`
2. Add an `elif provider == "my_provider"` branch in [src/models/\_\_init\_\_.py](../src/models/__init__.py) `create_model_interface`
3. (Optional) Add discovery to `src/utils/model_providers.py` so the Web UI can populate model lists
4. (Optional) Add a `MyProviderSection` component to `frontend/src/components/model-selection/`
5. Smoke-test by calling `create_model_interface("my_provider", ...)` directly

Full walkthrough with the `query()` result-dict shape and pitfalls: [`add-model-provider`](../.claude/skills/add-model-provider/SKILL.md) skill.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ollama.ResponseError: connection refused` | Daemon not running | `ollama serve` in another shell |
| `No model providers available` | Ollama not installed | `curl -fsSL https://ollama.ai/install.sh \| sh && ollama serve` |
| All `response: ""` in result file | Auth failed for OpenAI-compatible / model name wrong | Check `model_info.error` in the result entry |
| `was_truncated` always `false` on long outputs | Provider's response payload doesn't include token counts | Interface returns `0` for `tokens_generated`; flag falls back to `false`. Cosmetic only |
| First query slow (3–5 s) on Ollama | Cold model load | Expected — subsequent queries hit the cached model |

---

*See also: [PROJECT_OVERVIEW.md § Model Providers](PROJECT_OVERVIEW.md#model-providers), [PROMPT_STUDIO.md](PROMPT_STUDIO.md) for system-prompt resolution, [add-model-provider skill](../.claude/skills/add-model-provider/SKILL.md) for the full add-provider walkthrough.*
