"""Ollama model interface using only the standard library (urllib)."""

import json
import time
import urllib.request
from typing import Any, Dict

from src.models.BaseModelInterface import ModelInterface


class OllamaInterface(ModelInterface):
    """Interface for Ollama's ``/api/generate`` endpoint.

    Uses :mod:`urllib` so there is no dependency on the ``ollama`` package.
    """

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    # Phase 3: map Ollama's `done_reason` values to the provider-normalised
    # `finish_reason` contract documented in BaseModelInterface. Ollama may
    # emit `"stop"`, `"length"`, `"load"`, `"unload"`; only `"length"` means
    # the generation was truncated by the token limit. Everything else
    # collapses to `"stop"` for consumers.
    _DONE_REASON_TO_FINISH = {
        "length": "length",
        "stop": "stop",
        "load": "stop",
        "unload": "stop",
    }

    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        num_predict = params.get("max_tokens", 2048)
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            # Pass think=False when no_think is set; models that don't support
            # thinking ignore this field.  When think=True (default), Ollama
            # returns a separate "thinking" field in the response.
            "think": not params.get("no_think", False),
            "options": {
                "temperature": params.get("temperature", 0.1),
                "top_k": params.get("top_k", 40),
                "top_p": params.get("top_p", 0.9),
                "min_p": params.get("min_p", 0.05),
                "num_predict": num_predict,
            },
        }

        if params.get("system_prompt"):
            data["system"] = params["system_prompt"]

        start_time = time.time()
        try:
            request_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=request_data,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=params.get("timeout_seconds", 300)) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            end_time = time.time()

            done_reason = result.get("done_reason")
            finish_reason = self._DONE_REASON_TO_FINISH.get(done_reason, "stop") if done_reason else None

            return {
                "response": result.get("response", ""),
                # "thinking" is populated by Ollama for thinking-capable models
                # when think=True.  We surface it as "reasoning" so callers use
                # a provider-agnostic key.
                "reasoning": result.get("thinking") or None,
                "tokens_input": result.get("prompt_eval_count", 0),
                "tokens_generated": result.get("eval_count", 0),
                # Phase 3: provider stop-reason for was_truncated computation.
                # `num_predict = -1` is Ollama's "unlimited" sentinel — we
                # surface it as None so write-time fallback doesn't compare
                # against a negative cap.
                "finish_reason": finish_reason,
                "max_tokens_used": num_predict if isinstance(num_predict, int) and num_predict > 0 else None,
                "duration": end_time - start_time,
                "model_info": {"name": self.model_name, "provider": "ollama"},
            }

        except Exception as e:
            end_time = time.time()
            return {
                "error": str(e),
                "duration": end_time - start_time,
                "model_info": {"name": self.model_name, "provider": "ollama"},
            }
