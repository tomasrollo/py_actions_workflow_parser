"""SequenceDefinition — an ordered list of a single item type."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import DEFINITION, ITEM_TYPE, SEQUENCE
from .definition import Definition
from .definition_type import DefinitionType

if TYPE_CHECKING:
    from ..tokens.mapping_token import MappingToken
    from .template_schema import TemplateSchema


class SequenceDefinition(Definition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        self.item_type: str = ""

        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == SEQUENCE:
                    mapping = pair.value.assert_mapping(f"{DEFINITION} {SEQUENCE}")
                    for mp in mapping:
                        mk = mp.key.assert_string(f"{DEFINITION} {SEQUENCE} key")
                        if mk.value == ITEM_TYPE:
                            self.item_type = mp.value.assert_string(
                                f"{DEFINITION} {SEQUENCE} {ITEM_TYPE}"
                            ).value
                        else:
                            mk.assert_unexpected_value(f"{DEFINITION} {SEQUENCE} key")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.Sequence

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        if not self.item_type:
            raise ValueError(f"'{name}' does not defined '{ITEM_TYPE}'")
        schema.get_definition(self.item_type)
