"""HuggingFace Transformers model interface with proper MPS support."""

import re as _re
import time
from typing import Any, Dict, Tuple

_THINK_RE = _re.compile(r"<think>(.*?)</think>", _re.DOTALL)

from src.models.BaseModelInterface import ModelInterface

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class HuggingFaceInterface(ModelInterface):
    """Interface for HuggingFace Transformers models.

    Supports CUDA, Apple Silicon MPS, and CPU backends.  Models are loaded
    lazily on first query and cached for subsequent calls.
    """

    def __init__(self, model_name: str):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "HuggingFace interface requires 'transformers' and 'torch' packages. "
                "Install with: pip install transformers torch"
            )

        self.model_name = model_name

        # Device selection: CUDA > MPS > CPU
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        self._model = None
        self._tokenizer = None

    # -- lazy loading with caching -----------------------------------------

    def _ensure_loaded(self) -> Tuple:
        """Load model and tokenizer on first use."""
        if self._model is not None:
            return self._model, self._tokenizer

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # float16 works well on both CUDA and modern MPS; use float32 only on CPU
        dtype = torch.float32 if self.device == "cpu" else torch.float16

        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map=None,  # MPS does not support device_map
            low_cpu_mem_usage=True,
        )
        model = model.to(self.device)
        model.eval()

        self._model = model
        self._tokenizer = tokenizer
        return self._model, self._tokenizer

    # -- public API --------------------------------------------------------

    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        start_time = time.time()
        try:
            model, tokenizer = self._ensure_loaded()

            # Combine system + user prompt
            if params.get("system_prompt"):
                full_prompt = f"{params['system_prompt']}\n\n{prompt}"
            else:
                full_prompt = prompt

            # Tokenize and move to device
            inputs = tokenizer(full_prompt, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            max_new_tokens = params.get("max_tokens", 2048)
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=max(params.get("temperature", 0.1), 1e-7),
                    top_k=params.get("top_k", 40),
                    top_p=params.get("top_p", 0.9),
                    do_sample=params.get("temperature", 0.1) > 0,
                    pad_token_id=tokenizer.eos_token_id,
                )

            # Decode only the newly generated tokens
            input_len = inputs["input_ids"].shape[1]
            response_tokens = outputs[0][input_len:]
            response = tokenizer.decode(response_tokens, skip_special_tokens=True).strip()

            # Local thinking models (e.g. qwen3) embed <think>…</think> inline.
            # Strip and return separately so parsers receive a clean answer.
            reasoning: str | None = None
            m = _THINK_RE.search(response)
            if m:
                reasoning = m.group(1).strip()
                response = _THINK_RE.sub("", response).strip()

            # Phase 3: Transformers' `generate()` doesn't expose a finish-
            # reason primitive, but the token-count ratio is authoritative
            # when the EOS token isn't the last emitted token. Hitting
            # `max_new_tokens` exactly means the length cap truncated the
            # generation — callers treat this identically to a provider
            # that returned finish_reason="length".
            tokens_generated = len(response_tokens)
            finish_reason = (
                "length"
                if isinstance(max_new_tokens, int) and tokens_generated >= max_new_tokens
                else "stop"
            )

            end_time = time.time()
            return {
                "response": response,
                "reasoning": reasoning,
                "tokens_input": input_len,
                "tokens_generated": tokens_generated,
                "finish_reason": finish_reason,
                "max_tokens_used": max_new_tokens if isinstance(max_new_tokens, int) and max_new_tokens > 0 else None,
                "duration": end_time - start_time,
                "model_info": {"name": self.model_name, "provider": "huggingface"},
            }

        except Exception as e:
            end_time = time.time()
            return {
                "error": str(e),
                "duration": end_time - start_time,
                "model_info": {"name": self.model_name, "provider": "huggingface"},
            }

    def clear_cache(self):
        """Release model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        if TRANSFORMERS_AVAILABLE and self.device == "mps":
            torch.mps.empty_cache()
        elif TRANSFORMERS_AVAILABLE and self.device == "cuda":
            torch.cuda.empty_cache()