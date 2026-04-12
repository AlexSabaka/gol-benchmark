"""Matrix generation + execution endpoints for single-plugin benchmark sweeps."""
from __future__ import annotations

import json
import re
import uuid
from itertools import product
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.plugins import PluginRegistry
from src.plugins.base import ConfigField
from src.web.api.execution import RunRequest, submit_run
from src.web.api.testsets import GenerateRequest, PromptConfig, TaskConfig, generate_testset

router = APIRouter()

_SUPPORTED_FIELD_TYPES = {"number", "select", "boolean", "multi-select"}
_FIELD_TYPE_ALIASES = {"checkbox": "boolean"}


class MatrixPromptAxes(BaseModel):
    user_styles: List[str] = Field(default_factory=lambda: ["minimal"], min_length=1)
    system_styles: List[str] = Field(default_factory=lambda: ["analytical"], min_length=1)
    languages: List[str] = Field(default_factory=lambda: ["en"], min_length=1)


class MatrixFieldAxis(BaseModel):
    field_name: str
    values: List[Any] = Field(default_factory=list, min_length=1)


class MatrixModelGroup(BaseModel):
    provider: str = "ollama"
    models: List[str] = Field(min_length=1)
    ollama_host: str = "http://localhost:11434"
    api_key: str = ""
    api_base: str = ""


class MatrixRunRequest(BaseModel):
    plugin_type: str
    name_prefix: str = "matrix"
    description: str = ""
    generate_only: bool = False
    seed: int = 42
    temperature: float = 0.1
    max_tokens: int = 2048
    no_think: bool = True
    cell_markers: List[str] = Field(default_factory=lambda: ["1", "0"])
    custom_system_prompt: str | None = None
    base_generation: Dict[str, Any] = Field(default_factory=dict)
    prompt_axes: MatrixPromptAxes = Field(default_factory=MatrixPromptAxes)
    field_axes: List[MatrixFieldAxis] = Field(default_factory=list)
    model_groups: List[MatrixModelGroup] = Field(default_factory=list)


def _normalize_field_type(field_type: str) -> str:
    return _FIELD_TYPE_ALIASES.get(field_type, field_type)


def _unique_values(values: List[Any]) -> List[Any]:
    unique: List[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def _slugify(text: str, *, max_length: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        return "value"
    return slug[:max_length].strip("-") or "value"


def _field_value_slug(field_name: str, value: Any) -> str:
    return f"{_slugify(field_name, max_length=18)}-{_slugify(_display_value(value), max_length=24)}"


def _validate_axis_values(field: ConfigField, values: List[Any]) -> List[Any]:
    field_type = _normalize_field_type(field.field_type)
    validated: List[Any] = []

    for value in values:
        if field_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise HTTPException(400, f"Field '{field.name}' only accepts numeric variants")
            if field.min_value is not None and value < field.min_value:
                raise HTTPException(400, f"Field '{field.name}' has a minimum of {field.min_value}")
            if field.max_value is not None and value > field.max_value:
                raise HTTPException(400, f"Field '{field.name}' has a maximum of {field.max_value}")
            validated.append(value)
            continue

        if field_type == "boolean":
            if not isinstance(value, bool):
                raise HTTPException(400, f"Field '{field.name}' only accepts true/false variants")
            validated.append(value)
            continue

        if field_type == "select":
            options = field.options or []
            if value not in options:
                raise HTTPException(400, f"Field '{field.name}' variant '{value}' is not in the allowed options")
            validated.append(value)
            continue

        if field_type == "multi-select":
            options = set(field.options or [])
            if not isinstance(value, list):
                raise HTTPException(400, f"Field '{field.name}' requires each variant to be a list of options")
            if not value:
                raise HTTPException(400, f"Field '{field.name}' variants cannot be empty")
            invalid = [item for item in value if item not in options]
            if invalid:
                raise HTTPException(400, f"Field '{field.name}' has invalid options: {', '.join(str(item) for item in invalid)}")
            validated.append(value)
            continue

        raise HTTPException(400, f"Field '{field.name}' is not supported for matrix execution")

    return _unique_values(validated)


def _build_prompt_combinations(prompt_axes: MatrixPromptAxes) -> List[PromptConfig]:
    combos: List[PromptConfig] = []
    for user_style, system_style, language in product(
        prompt_axes.user_styles,
        prompt_axes.system_styles,
        prompt_axes.languages,
    ):
        combos.append(
            PromptConfig(
                user_style=user_style,
                system_style=system_style,
                language=language,
            )
        )
    return combos


def _build_field_combinations(field_axes: List[Tuple[str, List[Any]]]) -> List[Tuple[Dict[str, Any], List[str], List[str]]]:
    if not field_axes:
        return [({}, [], [])]

    names = [name for name, _ in field_axes]
    value_lists = [values for _, values in field_axes]
    combinations: List[Tuple[Dict[str, Any], List[str], List[str]]] = []
    for combo in product(*value_lists):
        values = dict(zip(names, combo))
        labels = [f"{name}={_display_value(value)}" for name, value in values.items()]
        slugs = [_field_value_slug(name, value) for name, value in values.items()]
        combinations.append((values, labels, slugs))
    return combinations


@router.post("/run")
async def run_matrix(req: MatrixRunRequest):
    """Generate one test set per matrix cell, then launch jobs for each selected model."""
    plugin = PluginRegistry.get(req.plugin_type)
    if plugin is None:
        raise HTTPException(404, f"Unknown plugin: {req.plugin_type}")

    if not req.generate_only and not req.model_groups:
        raise HTTPException(400, "Select at least one model group unless generate_only is enabled")

    generator = plugin.get_generator()
    schema = {field.name: field for field in generator.get_config_schema()}
    if not schema:
        raise HTTPException(400, f"Plugin '{req.plugin_type}' does not expose a generation schema")

    prompt_combinations = _build_prompt_combinations(req.prompt_axes)
    if not prompt_combinations:
        raise HTTPException(400, "At least one prompt combination is required")

    seen_field_names: set[str] = set()
    field_axes: List[Tuple[str, List[Any]]] = []
    for axis in req.field_axes:
        if axis.field_name in seen_field_names:
            raise HTTPException(400, f"Field '{axis.field_name}' was selected more than once")
        seen_field_names.add(axis.field_name)

        field = schema.get(axis.field_name)
        if field is None:
            raise HTTPException(400, f"Field '{axis.field_name}' is not part of the {req.plugin_type} schema")

        field_type = _normalize_field_type(field.field_type)
        if field_type not in _SUPPORTED_FIELD_TYPES:
            raise HTTPException(400, f"Field '{axis.field_name}' uses unsupported type '{field.field_type}'")

        field_axes.append((axis.field_name, _validate_axis_values(field, axis.values)))

    field_combinations = _build_field_combinations(field_axes)
    batch_id = uuid.uuid4().hex[:8]
    safe_prefix = _slugify(req.name_prefix, max_length=24)

    generated_testsets: List[Dict[str, Any]] = []
    all_jobs: List[Dict[str, Any]] = []

    for index, (prompt_config, (field_values, field_labels, field_slugs)) in enumerate(
        product(prompt_combinations, field_combinations),
        start=1,
    ):
        prompt_labels = [
            f"user={prompt_config.user_style}",
            f"system={prompt_config.system_style}",
            f"lang={prompt_config.language}",
        ]
        prompt_slugs = [
            f"user-{_slugify(prompt_config.user_style, max_length=16)}",
            f"system-{_slugify(prompt_config.system_style, max_length=16)}",
            f"lang-{_slugify(prompt_config.language, max_length=8)}",
        ]
        cell_id = f"{batch_id}_cell_{index:03d}"
        cell_label = " | ".join(prompt_labels + field_labels)
        cell_slug = "__".join(prompt_slugs + field_slugs) if field_slugs else "__".join(prompt_slugs)

        generation = dict(req.base_generation)
        generation.update(field_values)

        metadata_extra = {
            "matrix_batch_id": batch_id,
            "matrix_cell_id": cell_id,
            "matrix_label": cell_label,
            "matrix_plugin": req.plugin_type,
            "matrix_axes": {
                "user_style": prompt_config.user_style,
                "system_style": prompt_config.system_style,
                "language": prompt_config.language,
                **field_values,
            },
        }
        description = req.description.strip()
        if description:
            description = f"{description}\n\nMatrix cell: {cell_label}"
        else:
            description = f"Matrix cell: {cell_label}"

        generate_req = GenerateRequest(
            name=f"{safe_prefix}_{index:03d}_{cell_slug}",
            description=description,
            tasks=[
                TaskConfig(
                    type=req.plugin_type,
                    generation=generation,
                    prompt_configs=[prompt_config],
                )
            ],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            no_thinking=req.no_think,
            cell_markers=req.cell_markers,
            seed=req.seed,
            custom_system_prompt=req.custom_system_prompt,
            metadata_extra=metadata_extra,
        )
        generated = await generate_testset(generate_req)
        generated_testsets.append(
            {
                "cell_id": cell_id,
                "cell_label": cell_label,
                "testset_path": generated["testset_path"],
                "filename": generated["filename"],
                "prompt_config": prompt_config.model_dump(),
                "generation": generation,
                "axis_values": metadata_extra["matrix_axes"],
            }
        )

        if not req.generate_only:
            for model_group in req.model_groups:
                run_req = RunRequest(
                    testset_path=generated["testset_path"],
                    models=model_group.models,
                    provider=model_group.provider,
                    ollama_host=model_group.ollama_host,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    no_think=req.no_think,
                    api_key=model_group.api_key,
                    api_base=model_group.api_base,
                )
                submitted = await submit_run(run_req)
                for job in submitted["jobs"]:
                    all_jobs.append(
                        {
                            **job,
                            "cell_id": cell_id,
                            "cell_label": cell_label,
                            "testset_filename": generated["filename"],
                            "run_group_id": submitted.get("run_group_id"),
                        }
                    )

    return {
        "status": "ok",
        "batch_id": batch_id,
        "plugin_type": req.plugin_type,
        "generate_only": req.generate_only,
        "total_cells": len(generated_testsets),
        "total_jobs": len(all_jobs),
        "generated_testsets": generated_testsets,
        "jobs": all_jobs,
    }