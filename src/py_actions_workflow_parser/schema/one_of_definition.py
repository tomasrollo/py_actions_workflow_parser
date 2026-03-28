"""OneOfDefinition — a union of other definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import (
    ALLOWED_VALUES,
    BOOLEAN,
    CONSTANT,
    DEFINITION,
    LOOSE_KEY_TYPE,
    NULL,
    NUMBER,
    ONE_OF,
    SCALAR,
    SEQUENCE,
)
from .definition import Definition
from .definition_type import DefinitionType

if TYPE_CHECKING:
    from ..tokens.mapping_token import MappingToken
    from .mapping_definition import MappingDefinition
    from .property_definition import PropertyDefinition
    from .template_schema import TemplateSchema


class OneOfDefinition(Definition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        self.one_of: list[str] = []

        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == ONE_OF:
                    seq = pair.value.assert_sequence(f"{DEFINITION} {ONE_OF}")
                    for item in seq:
                        self.one_of.append(
                            item.assert_string(f"{DEFINITION} {ONE_OF} item").value
                        )
                elif dk.value == ALLOWED_VALUES:
                    seq = pair.value.assert_sequence(f"{DEFINITION} {ALLOWED_VALUES}")
                    for item in seq:
                        val = item.assert_string(f"{DEFINITION} {ONE_OF} item").value
                        self.one_of.append(f"{self.key}-{val}")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.OneOf

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        if not self.one_of:
            raise ValueError(f"'{name}' does not contain any references")

        from .mapping_definition import MappingDefinition
        from .sequence_definition import SequenceDefinition
        from .simple_definitions import (
            NullDefinition,
            BooleanDefinition,
            NumberDefinition,
        )
        from .string_definition import StringDefinition

        found_loose_key_type = False
        mapping_definitions: list[MappingDefinition] = []
        allowed_values_definition: OneOfDefinition | None = None
        sequence_definition: SequenceDefinition | None = None
        null_definition: NullDefinition | None = None
        boolean_definition: BooleanDefinition | None = None
        number_definition: NumberDefinition | None = None
        string_definitions: list[StringDefinition] = []
        seen_nested: dict[str, bool] = {}

        for nested_type in self.one_of:
            if seen_nested.get(nested_type):
                raise ValueError(
                    f"'{name}' contains duplicate nested type '{nested_type}'"
                )
            seen_nested[nested_type] = True

            nested = schema.get_definition(nested_type)
            if nested.reader_context:
                raise ValueError(
                    f"'{name}' is a one-of definition and references another definition that defines context. "
                    "This is currently not supported."
                )

            dt = nested.definition_type
            if dt == DefinitionType.Mapping:
                md = nested  # type: ignore[assignment]
                mapping_definitions.append(md)  # type: ignore[arg-type]
                if md.loose_key_type:  # type: ignore[attr-defined]
                    found_loose_key_type = True
            elif dt == DefinitionType.Sequence:
                if sequence_definition is not None:
                    raise ValueError(
                        f"'{name}' refers to more than one definition of type '{SEQUENCE}'"
                    )
                sequence_definition = nested  # type: ignore[assignment]
            elif dt == DefinitionType.Null:
                if null_definition is not None:
                    raise ValueError(
                        f"'{name}' refers to more than one definition of type '{NULL}'"
                    )
                null_definition = nested  # type: ignore[assignment]
            elif dt == DefinitionType.Boolean:
                if boolean_definition is not None:
                    raise ValueError(
                        f"'{name}' refers to more than one definition of type '{BOOLEAN}'"
                    )
                boolean_definition = nested  # type: ignore[assignment]
            elif dt == DefinitionType.Number:
                if number_definition is not None:
                    raise ValueError(
                        f"'{name}' refers to more than one definition of type '{NUMBER}'"
                    )
                number_definition = nested  # type: ignore[assignment]
            elif dt == DefinitionType.String:
                sd = nested  # type: ignore[assignment]
                if string_definitions and (not string_definitions[0].constant or not sd.constant):  # type: ignore[attr-defined]
                    raise ValueError(
                        f"'{name}' refers to more than one '{SCALAR}', but some do not set '{CONSTANT}'"
                    )
                string_definitions.append(sd)  # type: ignore[arg-type]
            elif dt == DefinitionType.OneOf:
                if allowed_values_definition is not None:
                    raise ValueError(
                        f"'{name}' contains multiple allowed-values definitions"
                    )
                allowed_values_definition = nested  # type: ignore[assignment]
            else:
                raise ValueError(
                    f"'{name}' refers to a definition with type '{nested.definition_type}'"
                )

        if len(mapping_definitions) > 1:
            if found_loose_key_type:
                raise ValueError(
                    f"'{name}' refers to two mappings and at least one sets '{LOOSE_KEY_TYPE}'. "
                    "This is not currently supported."
                )
            seen_props: dict[str, PropertyDefinition] = {}
            for md in mapping_definitions:
                for prop_name, new_prop in md.properties.items():
                    existing = seen_props.get(prop_name)
                    if existing:
                        if existing.type != new_prop.type:
                            raise ValueError(
                                f"'{name}' contains two mappings with the same property, but each refers to a "
                                "different type. All matching properties must refer to the same type."
                            )
                    else:
                        seen_props[prop_name] = new_prop
