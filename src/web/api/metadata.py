"""Benchmark metadata endpoint — exposes prompt style and language enums."""
import logging
from typing import Any

from fastapi import APIRouter

from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle
from src.web import prompt_store as prompt_store_module

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
def get_metadata() -> dict[str, Any]:
    """Return the canonical lists of languages and prompt styles, plus the
    Prompt Studio catalog (id / name / latest_version) so the matrix wizard
    can build a prompt-axis multi-select without a second round-trip.
    """
    prompts: list[dict[str, Any]] = []
    try:
        store = prompt_store_module.get_store()
        for p in store.list_prompts():
            languages = sorted(_languages_for(store, p["id"], p["latest_version"]))
            prompts.append(
                {
                    "id": p["id"],
                    "name": p["name"],
                    "latest_version": p["latest_version"],
                    "is_builtin": p["is_builtin"],
                    "language_codes": languages,
                }
            )
    except RuntimeError:
        # PromptStore not initialised (e.g. tests that don't spin a DB).
        # Falling back to an empty catalog keeps the endpoint usable.
        logger.debug("PromptStore unavailable; metadata.prompts empty")

    return {
        "languages":     [lang.value for lang in Language],
        "user_styles":   [s.value for s in PromptStyle],
        "system_styles": [s.value for s in SystemPromptStyle],
        "prompts":       prompts,
    }


def _languages_for(store: Any, prompt_id: str, version: int | None) -> set[str]:
    """Return the set of language codes present (and non-empty) on a version."""
    if version is None:
        return set()
    record = store.get_version(prompt_id, version)
    if record is None:
        return set()
    return {lang for lang, text in record["content"].items() if text}
