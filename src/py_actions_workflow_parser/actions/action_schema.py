"""ActionSchema — loads and caches the action JSON schema."""

from __future__ import annotations

import importlib.resources

from ..schema.template_schema import TemplateSchema
from ..templates.json_object_reader import JSONObjectReader

_schema: TemplateSchema | None = None


def get_action_schema() -> TemplateSchema:
    """Return the cached action schema, loading it on first call."""
    global _schema
    if _schema is None:
        ref = importlib.resources.files("py_actions_workflow_parser._schemas").joinpath(
            "action-v1.0.json"
        )
        with importlib.resources.as_file(ref) as path:
            raw = path.read_text(encoding="utf-8")
        _schema = TemplateSchema.load(JSONObjectReader(None, raw))
    return _schema
