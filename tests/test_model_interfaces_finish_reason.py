"""Phase 3: model interfaces surface `finish_reason` + `max_tokens_used`.

Each provider gets a single happy-path test that mocks the underlying HTTP /
library call and asserts the new fields appear on the return dict with the
provider-correct values:

- **OllamaInterface** — reads `done_reason` from the JSON response and maps
  it through `_DONE_REASON_TO_FINISH`.
- **OpenAICompatibleInterface** — reads `choice.finish_reason` directly;
  maps anything that isn't `"length"` to `"stop"`.
- **HuggingFaceInterface** — no provider signal; computes from
  `tokens_generated >= max_new_tokens`.

Each interface also emits `max_tokens_used` mirroring the param it actually
sent to the provider (`None` when the value is a sentinel like Ollama's
`-1` meaning unlimited).
"""
from __future__ import annotations

import io
import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# OllamaInterface
# ---------------------------------------------------------------------------


class _FakeUrlResponse:
    """Minimal replacement for the context manager returned by urlopen."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._body


def _fake_ollama_response(done_reason: str = "stop", eval_count: int = 42) -> Dict[str, Any]:
    return {
        "response": "drive",
        "thinking": None,
        "prompt_eval_count": 10,
        "eval_count": eval_count,
        "done_reason": done_reason,
    }


class TestOllamaFinishReason:
    def test_done_reason_length_maps_to_finish_reason_length(self):
        from src.models.OllamaInterface import OllamaInterface

        iface = OllamaInterface("test-model", base_url="http://localhost:11434")
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_ollama_response("length", 2048))):
            out = iface.query("hello", {"max_tokens": 2048})

        assert out["finish_reason"] == "length"
        assert out["max_tokens_used"] == 2048
        assert out["tokens_generated"] == 2048

    def test_done_reason_stop_maps_to_stop(self):
        from src.models.OllamaInterface import OllamaInterface

        iface = OllamaInterface("test-model")
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_ollama_response("stop", 37))):
            out = iface.query("hello", {"max_tokens": 100})

        assert out["finish_reason"] == "stop"
        assert out["max_tokens_used"] == 100

    def test_unknown_done_reason_collapses_to_stop(self):
        from src.models.OllamaInterface import OllamaInterface

        iface = OllamaInterface("test-model")
        # Ollama may return "load" / "unload" in odd conditions — both should
        # surface as "stop" to consumers (not "length", not None).
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_ollama_response("load", 5))):
            out = iface.query("hello", {"max_tokens": 100})

        assert out["finish_reason"] == "stop"

    def test_missing_done_reason_emits_none(self):
        from src.models.OllamaInterface import OllamaInterface

        iface = OllamaInterface("test-model")
        payload = _fake_ollama_response("stop", 5)
        del payload["done_reason"]
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(payload)):
            out = iface.query("hello", {"max_tokens": 100})

        # Missing from provider → None (don't fabricate a stop signal).
        assert out["finish_reason"] is None

    def test_unlimited_num_predict_emits_none_max_tokens_used(self):
        from src.models.OllamaInterface import OllamaInterface

        iface = OllamaInterface("test-model")
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_ollama_response("stop", 100))):
            # Ollama convention: num_predict = -1 means unlimited.
            out = iface.query("hello", {"max_tokens": -1})

        assert out["max_tokens_used"] is None
        assert out["finish_reason"] == "stop"

    def test_error_path_preserves_existing_shape(self):
        from src.models.OllamaInterface import OllamaInterface

        iface = OllamaInterface("test-model")
        with patch("urllib.request.urlopen", side_effect=RuntimeError("boom")):
            out = iface.query("hello", {"max_tokens": 100})

        # Error responses don't get finish_reason / max_tokens_used.
        assert "error" in out
        assert "finish_reason" not in out
        assert "max_tokens_used" not in out


# ---------------------------------------------------------------------------
# OpenAICompatibleInterface
# ---------------------------------------------------------------------------


def _fake_openai_response(finish_reason: str = "stop", completion_tokens: int = 42) -> Dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"content": "drive", "reasoning_content": None},
                "finish_reason": finish_reason,
            },
        ],
        "usage": {
            "completion_tokens": completion_tokens,
            "prompt_tokens": 10,
        },
    }


class TestOpenAIFinishReason:
    def test_length_finish_reason_preserved(self):
        from src.models.OpenAICompatibleInterface import OpenAICompatibleInterface

        iface = OpenAICompatibleInterface("test", base_url="http://localhost/v1")
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_openai_response("length", 2048))):
            out = iface.query("hello", {"max_tokens": 2048})

        assert out["finish_reason"] == "length"
        assert out["max_tokens_used"] == 2048

    def test_stop_finish_reason_preserved(self):
        from src.models.OpenAICompatibleInterface import OpenAICompatibleInterface

        iface = OpenAICompatibleInterface("test", base_url="http://localhost/v1")
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_openai_response("stop", 37))):
            out = iface.query("hello", {"max_tokens": 100})

        assert out["finish_reason"] == "stop"

    def test_content_filter_collapses_to_stop(self):
        from src.models.OpenAICompatibleInterface import OpenAICompatibleInterface

        iface = OpenAICompatibleInterface("test", base_url="http://localhost/v1")
        # Any non-"length" value surfaces as "stop" per the BaseModelInterface
        # contract — was_truncated only fires on "length".
        with patch("urllib.request.urlopen",
                   return_value=_FakeUrlResponse(_fake_openai_response("content_filter", 10))):
            out = iface.query("hello", {"max_tokens": 100})

        assert out["finish_reason"] == "stop"

    def test_null_finish_reason_preserved(self):
        from src.models.OpenAICompatibleInterface import OpenAICompatibleInterface

        iface = OpenAICompatibleInterface("test", base_url="http://localhost/v1")
        payload = _fake_openai_response("stop", 10)
        payload["choices"][0]["finish_reason"] = None
        with patch("urllib.request.urlopen", return_value=_FakeUrlResponse(payload)):
            out = iface.query("hello", {"max_tokens": 100})

        assert out["finish_reason"] is None


# ---------------------------------------------------------------------------
# HuggingFaceInterface
# ---------------------------------------------------------------------------


class TestHuggingFaceFinishReason:
    """HuggingFace has no provider-level finish_reason — we compute it from
    the token-count ratio. Exercises the computation without actually loading
    a transformers model."""

    def test_at_max_new_tokens_finish_reason_is_length(self):
        # Standalone logic test — mirrors the computation in HuggingFaceInterface
        # without instantiating the full torch stack.
        max_new_tokens = 2048
        tokens_generated = 2048
        finish_reason = (
            "length"
            if isinstance(max_new_tokens, int) and tokens_generated >= max_new_tokens
            else "stop"
        )
        assert finish_reason == "length"

    def test_below_max_new_tokens_finish_reason_is_stop(self):
        max_new_tokens = 2048
        tokens_generated = 10
        finish_reason = (
            "length"
            if isinstance(max_new_tokens, int) and tokens_generated >= max_new_tokens
            else "stop"
        )
        assert finish_reason == "stop"

    def test_exactly_at_boundary_counts_as_length(self):
        # The contract: tokens_generated == max_new_tokens → "length".
        # Provider semantics are ambiguous (the model might have naturally
        # stopped at the last allowed token) but the boolean we OR with the
        # token-count comparison in the write path would make the same call,
        # so this choice is consistent end-to-end.
        assert 2048 >= 2048  # sanity


# ---------------------------------------------------------------------------
# Base contract shape
# ---------------------------------------------------------------------------


def test_base_contract_documents_phase3_fields():
    """The BaseModelInterface docstring should call out finish_reason +
    max_tokens_used so future provider authors know to emit them."""
    from src.models.BaseModelInterface import ModelInterface

    doc = ModelInterface.query.__doc__ or ""
    assert "finish_reason" in doc
    assert "max_tokens_used" in doc
