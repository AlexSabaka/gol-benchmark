"""OpenAI-compatible chat-completions interface (Groq, OpenRouter, vLLM, LM Studio, etc.)."""

import json
import re
import time
import urllib.request
from typing import Any, Dict

from src.models.BaseModelInterface import ModelInterface


def _normalize_base_url(url: str) -> str:
    """Ensure *url* ends with a ``/v…`` version segment.

    Many providers require the ``/v1`` path prefix.  If the caller passes a
    bare host (e.g. ``http://localhost:8080``) this function appends ``/v1``
    so that ``{base_url}/chat/completions`` resolves correctly.

    URLs that already contain a version segment (``/v1``, ``/v2``, …) are
    returned unchanged (after stripping a trailing slash).
    """
    url = url.rstrip("/")
    # Already has a /vN segment at the end of the path?  Leave it alone.
    if re.search(r"/v\d+$", url):
        return url
    return f"{url}/v1"


class OpenAICompatibleInterface(ModelInterface):
    """Interface for any OpenAI-compatible ``/v1/chat/completions`` endpoint."""

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434/v1",
                 api_key: str = ""):
        self.model_name = model_name
        self.base_url = _normalize_base_url(base_url)
        self.api_key = api_key

    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        messages = []
        if params.get("system_prompt"):
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": params.get("temperature", 0.1),
            "max_tokens": params.get("max_tokens", 2048),
            "stream": False,
        }

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        start_time = time.time()
        try:
            request_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=request_data,
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=params.get("timeout_seconds", 120)) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            end_time = time.time()
            choice = result.get("choices", [{}])[0]
            text = choice.get("message", {}).get("content", "")
            usage = result.get("usage", {})

            return {
                "response": text,
                "tokens_generated": usage.get("completion_tokens", 0),
                "tokens_input": usage.get("prompt_tokens", 0),
                "duration": end_time - start_time,
                "model_info": {"name": self.model_name, "provider": "openai_compatible"},
            }
        except Exception as e:
            end_time = time.time()
            return {
                "error": str(e),
                "duration": end_time - start_time,
                "model_info": {"name": self.model_name, "provider": "openai_compatible"},
            }
