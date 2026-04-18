"""Benchmark metadata endpoint — exposes prompt style and language enums."""
from fastapi import APIRouter

from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle

router = APIRouter()


@router.get("")
def get_metadata():
    """Return the canonical lists of languages and prompt styles."""
    return {
        "languages":     [lang.value for lang in Language],
        "user_styles":   [s.value for s in PromptStyle],
        "system_styles": [s.value for s in SystemPromptStyle],
    }
