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


@router.get("/{task_type}/schema")
async def plugin_schema(task_type: str):
    """Return the configuration schema for a given task type."""
    plugin = PluginRegistry.get(task_type)
    if plugin is None:
        return {"task_type": task_type, "fields": [], "groups": []}

    generator = plugin.get_generator()
    schema_fields = generator.get_config_schema()

    fields = [f.to_dict() for f in schema_fields]
    groups = list(dict.fromkeys(f.group for f in schema_fields))
    return {"task_type": task_type, "fields": fields, "groups": groups}
