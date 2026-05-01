"""Prompt Studio CRUD endpoints — versioned, user-managed system prompts.

Routes register under ``/api/prompts``. The store
(:mod:`src.web.prompt_store`) is the canonical source; PromptEngine
(``src/core/PromptEngine.py``) survives only as the seed material for
``builtin_*`` prompts and as a last-resort fallback for code paths that
don't go through the web app (CLI scripts, tests).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.web import prompt_store as prompt_store_module
from src.web.prompt_store import (
    PromptNotFoundError,
    PromptSlugConflictError,
    PromptStoreError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class PromptSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    is_builtin: bool
    tags: list[str]
    archived_at: str | None
    created_at: str
    created_by: str | None
    updated_at: str
    latest_version: int | None
    language_codes: list[str] = []


class PromptDetail(PromptSummary):
    content: dict[str, str]
    change_note: str


class PromptVersionMeta(BaseModel):
    version: int
    parent_version: int | None
    change_note: str
    created_at: str
    created_by: str | None


class PromptVersionDetail(BaseModel):
    prompt_id: str
    version: int
    parent_version: int | None
    change_note: str
    content: dict[str, str]
    created_at: str
    created_by: str | None


class CreatePromptRequest(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str | None = None
    description: str = ""
    content: dict[str, str]
    tags: list[str] = Field(default_factory=list)
    created_by: str | None = None


class CreateVersionRequest(BaseModel):
    content: dict[str, str]
    change_note: str = ""
    parent_version: int | None = None
    created_by: str | None = None


class UpdatePromptRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class CreatedResponse(BaseModel):
    prompt_id: str


class VersionCreatedResponse(BaseModel):
    prompt_id: str
    version: int


class OkResponse(BaseModel):
    ok: bool = True


class TranslatePromptRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)
    source_lang: str = "en"
    target_langs: list[str] = Field(..., min_length=1, max_length=6)


class TranslatePromptResponse(BaseModel):
    translations: dict[str, str]
    provider: str
    failed: list[str] = []


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[PromptSummary])
async def list_prompts(include_archived: bool = False) -> list[dict[str, Any]]:
    """List every prompt (optionally including archived)."""
    return prompt_store_module.get_store().list_prompts(
        include_archived=include_archived
    )


@router.post("", response_model=CreatedResponse, status_code=201)
async def create_prompt(request: CreatePromptRequest) -> CreatedResponse:
    """Create a user-authored prompt at v1."""
    store = prompt_store_module.get_store()
    try:
        prompt_id = store.create_prompt(
            name=request.name,
            slug=request.slug,
            description=request.description,
            content=request.content,
            tags=request.tags,
            created_by=request.created_by,
        )
    except PromptSlugConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PromptStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreatedResponse(prompt_id=prompt_id)


@router.post("/translate", response_model=TranslatePromptResponse)
async def translate_prompt_text(
    request: TranslatePromptRequest,
) -> TranslatePromptResponse:
    """Batch-translate ``text`` from ``source_lang`` to each ``target_langs``.

    Per-target failures are non-fatal — listed in ``failed[]`` so the editor
    can populate whatever succeeded and let the user retry the rest. Reuses
    the LRU-cached :func:`src.web.translation.translate` helper used by Human
    Review.
    """
    from src.web.translation import translate, TranslationError

    out: dict[str, str] = {}
    failed: list[str] = []
    provider = ""
    for tgt in request.target_langs:
        try:
            r = translate(request.text, request.source_lang, tgt)
            out[tgt] = r.translated
            provider = r.provider
        except TranslationError as exc:
            logger.warning("translate %s→%s failed: %s", request.source_lang, tgt, exc)
            failed.append(tgt)
    return TranslatePromptResponse(
        translations=out, provider=provider, failed=failed
    )


@router.get("/{prompt_id}", response_model=PromptDetail)
async def get_prompt(prompt_id: str) -> dict[str, Any]:
    detail = prompt_store_module.get_store().get_prompt(prompt_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    return detail


@router.patch("/{prompt_id}", response_model=OkResponse)
async def update_prompt(
    prompt_id: str, request: UpdatePromptRequest
) -> OkResponse:
    store = prompt_store_module.get_store()
    try:
        store.update_metadata(
            prompt_id,
            name=request.name,
            description=request.description,
            tags=request.tags,
        )
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PromptStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OkResponse()


@router.post("/{prompt_id}/archive", response_model=OkResponse)
async def archive_prompt(prompt_id: str) -> OkResponse:
    store = prompt_store_module.get_store()
    try:
        store.archive(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OkResponse()


@router.post("/{prompt_id}/restore", response_model=OkResponse)
async def restore_prompt(prompt_id: str) -> OkResponse:
    store = prompt_store_module.get_store()
    try:
        store.restore(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OkResponse()


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionMeta])
async def list_versions(prompt_id: str) -> list[dict[str, Any]]:
    store = prompt_store_module.get_store()
    try:
        return store.list_versions(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{prompt_id}/versions/{version}",
    response_model=PromptVersionDetail,
)
async def get_version(prompt_id: str, version: int) -> dict[str, Any]:
    detail = prompt_store_module.get_store().get_version(prompt_id, version)
    if detail is None:
        raise HTTPException(status_code=404, detail="version not found")
    return detail


@router.post(
    "/{prompt_id}/versions",
    response_model=VersionCreatedResponse,
    status_code=201,
)
async def create_version(
    prompt_id: str, request: CreateVersionRequest
) -> VersionCreatedResponse:
    store = prompt_store_module.get_store()
    try:
        version = store.create_version(
            prompt_id,
            content=request.content,
            change_note=request.change_note,
            parent_version=request.parent_version,
            created_by=request.created_by,
        )
    except PromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PromptStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VersionCreatedResponse(prompt_id=prompt_id, version=version)
