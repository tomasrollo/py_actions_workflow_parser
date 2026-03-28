"""MappingDefinition — a key-value mapping with typed properties."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import (
    DEFINITION,
    LOOSE_KEY_TYPE,
    LOOSE_VALUE_TYPE,
    MAPPING,
    PROPERTIES,
)
from .definition import Definition
from .definition_type import DefinitionType
from .property_definition import PropertyDefinition

if TYPE_CHECKING:
    from ..tokens.mapping_token import MappingToken
    from .template_schema import TemplateSchema


class MappingDefinition(Definition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        self.properties: dict[str, PropertyDefinition] = {}
        self.loose_key_type: str = ""
        self.loose_value_type: str = ""

        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == MAPPING:
                    mapping = pair.value.assert_mapping(f"{DEFINITION} {MAPPING}")
                    for mp in mapping:
                        mk = mp.key.assert_string(f"{DEFINITION} {MAPPING} key")
                        if mk.value == PROPERTIES:
                            props = mp.value.assert_mapping(
                                f"{DEFINITION} {MAPPING} {PROPERTIES}"
                            )
                            for pp in props:
                                prop_name = pp.key.assert_string(
                                    f"{DEFINITION} {MAPPING} {PROPERTIES} key"
                                )
                                self.properties[prop_name.value] = PropertyDefinition(
                                    pp.value
                                )
                        elif mk.value == LOOSE_KEY_TYPE:
                            self.loose_key_type = mp.value.assert_string(
                                f"{DEFINITION} {MAPPING} {LOOSE_KEY_TYPE}"
                            ).value
                        elif mk.value == LOOSE_VALUE_TYPE:
                            self.loose_value_type = mp.value.assert_string(
                                f"{DEFINITION} {MAPPING} {LOOSE_VALUE_TYPE}"
                            ).value
                        else:
                            mk.assert_unexpected_value(f"{DEFINITION} {MAPPING} key")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.Mapping

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        if self.loose_key_type:
            schema.get_definition(self.loose_key_type)
            if self.loose_value_type:
                schema.get_definition(self.loose_value_type)
            else:
                raise ValueError(
                    f"Property '{LOOSE_KEY_TYPE}' is defined but '{LOOSE_VALUE_TYPE}' is not defined on '{name}'"
                )
        elif self.loose_value_type:
            raise ValueError(
                f"Property '{LOOSE_VALUE_TYPE}' is defined but '{LOOSE_KEY_TYPE}' is not defined on '{name}'"
            )

        for prop_name, prop_def in self.properties.items():
            if not prop_def.type:
                raise ValueError(
                    f"Type not specified for the property '{prop_name}' on '{name}'"
                )
            schema.get_definition(prop_def.type)
