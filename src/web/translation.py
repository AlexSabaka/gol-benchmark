"""Machine-translation helper for the Human Review feature.

Thin wrapper around the `deep-translator` package so we can swap providers
without changing the API surface. Used by `POST /api/human-review/translate`.

Configuration (environment variables):

    TRANSLATOR_PROVIDER     google | libre | mymemory       (default: google)
    LIBRETRANSLATE_URL      URL for the libre provider      (default: http://localhost:5000)
    LIBRETRANSLATE_API_KEY  API key for libre provider      (default: empty)

`deep-translator` talks to public endpoints — no API keys required for the
Google provider, which makes local annotation work painless. For production or
bulk workloads, configure `libre` (self-hosted) instead.

The result of each translation is cached in-process via `functools.lru_cache`
keyed by `(text_hash, source_lang, target_lang)`. The hash avoids blowing out
the cache with long prompts while still giving O(1) hits on repeat reads.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when the translation backend fails or is unavailable."""


@dataclass(frozen=True)
class TranslationResult:
    translated: str
    provider: str
    source_lang: str
    target_lang: str


def _provider_name() -> str:
    return (os.environ.get("TRANSLATOR_PROVIDER") or "google").lower()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        return "auto"
    low = lang.lower()
    # Internal → provider-friendly tag remap. `ua` → `uk` (Ukrainian ISO 639-1);
    # `zh` on its own is ambiguous for Google/MyMemory (they want a script
    # variant) — default to Simplified (`zh-CN`) since that's how our testsets
    # are generated. If a user explicitly asks for Traditional, they'll pass
    # `zh-tw` which already lower-cases correctly for the providers.
    if low == "ua":
        return "uk"
    if low == "zh":
        return "zh-CN"
    return low


@lru_cache(maxsize=2048)
def _translate_cached(
    _text_hash: str,
    text: str,
    source: str,
    target: str,
    provider: str,
) -> TranslationResult:
    """Internal cache layer. `_text_hash` is part of the key so the cache
    dedupes identical text without paying repeated translator cost.
    """
    try:
        from deep_translator import GoogleTranslator, MyMemoryTranslator, LibreTranslator
    except ImportError as exc:  # pragma: no cover — surfaced at runtime
        raise TranslationError(
            "deep-translator is not installed. Run `pip install deep-translator`."
        ) from exc

    try:
        if provider == "libre":
            translator = LibreTranslator(
                source=source,
                target=target,
                base_url=os.environ.get("LIBRETRANSLATE_URL", "http://localhost:5000/"),
                api_key=os.environ.get("LIBRETRANSLATE_API_KEY") or None,
            )
        elif provider == "mymemory":
            translator = MyMemoryTranslator(source=source, target=target)
        else:
            translator = GoogleTranslator(source=source, target=target)

        translated = translator.translate(text)
    except Exception as exc:  # translation libraries throw a zoo of exceptions
        logger.warning("Translation failed (provider=%s): %s", provider, exc)
        raise TranslationError(f"Translation failed: {exc}") from exc

    if not isinstance(translated, str):
        raise TranslationError("Translation backend returned a non-string result")

    return TranslationResult(
        translated=translated,
        provider=provider,
        source_lang=source,
        target_lang=target,
    )


def translate(
    text: str,
    source_lang: Optional[str] = None,
    target_lang: str = "en",
) -> TranslationResult:
    """Translate `text` from `source_lang` → `target_lang`.

    `source_lang=None` triggers auto-detection (supported by all providers).
    Short-circuits when source == target (common case — UI offers Translate
    even when source already matches target).

    Raises:
        TranslationError: if the provider cannot satisfy the request.
    """
    if not text or not text.strip():
        raise TranslationError("Empty text")

    source = _normalize_lang(source_lang)
    target = _normalize_lang(target_lang) or "en"

    if source == target and source != "auto":
        # No-op: return the original text so clients can use the same code path.
        return TranslationResult(
            translated=text,
            provider="noop",
            source_lang=source,
            target_lang=target,
        )

    return _translate_cached(_hash_text(text), text, source, target, _provider_name())


def clear_cache() -> None:
    """Test helper — resets the LRU cache."""
    _translate_cached.cache_clear()
