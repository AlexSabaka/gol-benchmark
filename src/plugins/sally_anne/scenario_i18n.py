"""Sally-Anne scenario i18n — loaded from i18n.yaml.

All localized content for 6 languages: en, es, fr, de, zh, ua.
Covers narrative templates, question templates, objects, containers,
pronouns, names, and leave activities.

This module exposes the same dict names as before for backward
compatibility with scenario_builder.py.  Data is loaded from YAML.
"""
from src.plugins.i18n.loader import load_plugin_i18n

_data = load_plugin_i18n("sally_anne")

NARRATIVE_TEMPLATES = _data.get("narrative_templates", {})
QUESTION_TEMPLATES = _data.get("question_templates", {})
OBJECTS = _data.get("objects", {})
CONTAINERS = _data.get("containers", {})
PRONOUNS = _data.get("pronouns", {})
NAMES = _data.get("names", {})
LEAVE_ACTIVITIES = _data.get("leave_activities", {})
DISTRACTOR_TEMPLATE = _data.get("distractor_template", {})
DISTRACTOR_OBJECTS = _data.get("distractor_objects", {})
DISTRACTOR_LOCATIONS = _data.get("distractor_locations", {})
