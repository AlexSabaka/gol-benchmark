"""Plugin discovery & schema endpoints."""
from fastapi import APIRouter

from src.plugins import PluginRegistry

router = APIRouter()


@router.get("")
async def list_plugins():
    """List all registered benchmark plugins."""
    PluginRegistry._ensure_loaded()
    plugins = PluginRegistry.get_all()
    return [
        {
            "task_type": task_type,
            "display_name": p.display_name,
            "description": getattr(p, "description", ""),
            "version": getattr(p, "version", "1.0.0"),
        }
        for task_type, p in sorted(plugins.items())
    ]


# Field schema definitions for each task type — drives the dynamic config forms.
_TASK_SCHEMAS: dict = {
    "arithmetic": {
        "fields": [
            {"name": "complexity", "label": "Complexity levels", "type": "multi-select",
             "options": [1, 2, 3, 4, 5], "default": [2, 3]},
            {"name": "expressions_per_target", "label": "Expressions per target", "type": "number", "min": 1, "max": 500, "default": 10},
            {"name": "target_values", "label": "Target values", "type": "text", "default": "1,2,3,4,5",
             "help": "Comma-separated target result values"},
            {"name": "mode", "label": "Mode", "type": "select", "options": ["expression", "equation"], "default": "expression"},
        ]
    },
    "game_of_life": {
        "fields": [
            {"name": "difficulty_levels", "label": "Difficulty", "type": "multi-select",
             "options": ["EASY", "MEDIUM", "HARD", "NIGHTMARE"], "default": ["EASY", "MEDIUM"]},
            {"name": "grids_per_difficulty", "label": "Grids per difficulty", "type": "number", "min": 1, "max": 200, "default": 5},
            {"name": "density", "label": "Cell density", "type": "number", "min": 0.1, "max": 0.9, "step": 0.05, "default": 0.3},
            {"name": "known_patterns_ratio", "label": "Known patterns ratio", "type": "number", "min": 0.0, "max": 1.0, "step": 0.1, "default": 0.3},
        ]
    },
    "cellular_automata_1d": {
        "fields": [
            {"name": "rule_numbers", "label": "Rule numbers", "type": "multi-select",
             "options": [30, 54, 60, 90, 110, 150, 182], "default": [30, 90, 110]},
            {"name": "cases_per_rule", "label": "Cases per rule", "type": "number", "min": 1, "max": 200, "default": 5},
            {"name": "width", "label": "Grid width", "type": "number", "min": 5, "max": 50, "default": 11},
            {"name": "steps", "label": "Steps", "type": "number", "min": 1, "max": 20, "default": 3},
            {"name": "boundary_condition", "label": "Boundary", "type": "select",
             "options": ["wrap", "dead", "alive"], "default": "wrap"},
        ]
    },
    "linda_fallacy": {
        "fields": [
            {"name": "num_options", "label": "Options per question", "type": "number", "min": 3, "max": 10, "default": 5},
            {"name": "personas_per_config", "label": "Personas count", "type": "number", "min": 1, "max": 50, "default": 10},
        ]
    },
    "ascii_shapes": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
            {"name": "question_type", "label": "Question type", "type": "multi-select",
             "options": ["dimensions", "count", "position"], "default": ["dimensions", "count"]},
        ]
    },
    "object_tracking": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
            {"name": "num_objects", "label": "Objects", "type": "number", "min": 2, "max": 8, "default": 3},
            {"name": "num_containers", "label": "Containers", "type": "number", "min": 2, "max": 8, "default": 3},
        ]
    },
    "sally_anne": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
        ]
    },
    "carwash": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
        ]
    },
    "inverted_cup": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
        ]
    },
    "strawberry": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
        ]
    },
    "measure_comparison": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
        ]
    },
    "grid_tasks": {
        "fields": [
            {"name": "count", "label": "Number of cases", "type": "number", "min": 1, "max": 200, "default": 10},
            {"name": "min_rows", "label": "Min rows", "type": "number", "min": 2, "max": 20, "default": 3},
            {"name": "max_rows", "label": "Max rows", "type": "number", "min": 2, "max": 20, "default": 6},
        ]
    },
}


@router.get("/{task_type}/schema")
async def plugin_schema(task_type: str):
    """Return the configuration schema for a given task type."""
    schema = _TASK_SCHEMAS.get(task_type, {"fields": []})
    return {"task_type": task_type, **schema}
