"""DefinitionInfo — combineds a Definition with its accumulated allowed context."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .definition import Definition
    from .definition_type import DefinitionType
    from .scalar_definition import ScalarDefinition
    from .template_schema import TemplateSchema


class DefinitionInfo:
    is_definition_info = True

    def __init__(
        self,
        schema_or_parent: "TemplateSchema | DefinitionInfo",
        name_or_definition: "str | Definition",
    ) -> None:
        parent: DefinitionInfo | None = (
            schema_or_parent  # type: ignore[assignment]
            if getattr(schema_or_parent, "is_definition_info", False)
            else None
        )

        from .template_schema import TemplateSchema as _TemplateSchema  # noqa: F401

        self._schema: TemplateSchema = (
            parent._schema if parent is not None else schema_or_parent  # type: ignore[assignment]
        )

        # Look up definition by name if a string key was passed
        if isinstance(name_or_definition, str):
            self.definition: Definition = self._schema.get_definition(
                name_or_definition
            )
        else:
            self.definition = name_or_definition

        # Accumulate allowed context
        if self.definition.reader_context:
            self.allowed_context: list[str] = []
            upper_seen: dict[str, bool] = {}

            # Copy parent's allowed context first
            parent_context = parent.allowed_context if parent is not None else []
            for ctx in parent_context:
                self.allowed_context.append(ctx)
                upper_seen[ctx.upper()] = True

            # Append new context entries (case-insensitive dedup)
            for ctx in self.definition.reader_context:
                upper = ctx.upper()
                if not upper_seen.get(upper):
                    self.allowed_context.append(ctx)
                    upper_seen[upper] = True
        else:
            self.allowed_context = parent.allowed_context if parent is not None else []

    def get_scalar_definitions(self) -> "list[ScalarDefinition]":
        return self._schema.get_scalar_definitions(self.definition)

    def get_definitions_of_type(self, type: "DefinitionType") -> "list[Definition]":
        return self._schema.get_definitions_of_type(self.definition, type)
