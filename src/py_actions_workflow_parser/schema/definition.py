"""Abstract Definition base class for all schema definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..templates.template_constants import CONTEXT, DEFINITION, DESCRIPTION
from .definition_type import DefinitionType

if TYPE_CHECKING:
    from ..tokens.mapping_token import MappingToken
    from .template_schema import TemplateSchema


class Definition(ABC):
    """Defines the allowable schema for a user-defined type."""

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        self.key = key
        self.description: str | None = None
        self.reader_context: list[str] = []
        self.evaluator_context: list[str] = []

        if definition is not None:
            i = 0
            while i < definition.count:
                definition_key = definition.get(i).key.assert_string(
                    f"{DEFINITION} key"
                )
                if definition_key.value == CONTEXT:
                    context = definition.get(i).value.assert_sequence(
                        f"{DEFINITION} {CONTEXT}"
                    )
                    definition.remove(i)
                    seen_reader: dict[str, bool] = {}
                    seen_evaluator: dict[str, bool] = {}
                    for item in context:
                        item_str = item.assert_string(f"{CONTEXT} item").value
                        upper_item = item_str.upper()
                        if seen_reader.get(upper_item):
                            raise ValueError(f"Duplicate context item '{item_str}'")
                        seen_reader[upper_item] = True
                        self.reader_context.append(item_str)

                        # Strip min/max param info for evaluator context
                        paren = item_str.find("(")
                        modified = (
                            item_str[: paren + 1] + ")" if paren > 0 else item_str
                        )
                        upper_modified = modified.upper()
                        if seen_evaluator.get(upper_modified):
                            raise ValueError(f"Duplicate context item '{modified}'")
                        seen_evaluator[upper_modified] = True
                        self.evaluator_context.append(modified)
                elif definition_key.value == DESCRIPTION:
                    self.description = (
                        definition.get(i).value.assert_string(DESCRIPTION).value
                    )
                    definition.remove(i)
                else:
                    i += 1

    @property
    @abstractmethod
    def definition_type(self) -> DefinitionType: ...

    @abstractmethod
    def validate(self, schema: "TemplateSchema", name: str) -> None: ...
