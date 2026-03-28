"""NullDefinition, BooleanDefinition, NumberDefinition — simple scalar definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import BOOLEAN, DEFINITION, NULL, NUMBER
from ..tokens.types import TokenType
from .definition_type import DefinitionType
from .scalar_definition import ScalarDefinition

if TYPE_CHECKING:
    from ..tokens.literal_token import LiteralToken
    from ..tokens.mapping_token import MappingToken
    from .template_schema import TemplateSchema


class NullDefinition(ScalarDefinition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == NULL:
                    mapping = pair.value.assert_mapping(f"{DEFINITION} {NULL}")
                    for mp in mapping:
                        mk = mp.key.assert_string(f"{DEFINITION} {NULL} key")
                        mk.assert_unexpected_value(f"{DEFINITION} {NULL} key")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.Null

    def is_match(self, literal: "LiteralToken") -> bool:
        return literal.template_token_type == TokenType.Null

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        pass


class BooleanDefinition(ScalarDefinition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == BOOLEAN:
                    mapping = pair.value.assert_mapping(f"{DEFINITION} {BOOLEAN}")
                    for mp in mapping:
                        mk = mp.key.assert_string(f"{DEFINITION} {BOOLEAN} key")
                        mk.assert_unexpected_value(f"{DEFINITION} {BOOLEAN} key")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.Boolean

    def is_match(self, literal: "LiteralToken") -> bool:
        return literal.template_token_type == TokenType.Boolean

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        pass


class NumberDefinition(ScalarDefinition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == NUMBER:
                    mapping = pair.value.assert_mapping(f"{DEFINITION} {NUMBER}")
                    for mp in mapping:
                        mk = mp.key.assert_string(f"{DEFINITION} {NUMBER} key")
                        mk.assert_unexpected_value(f"{DEFINITION} {NUMBER} key")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.Number

    def is_match(self, literal: "LiteralToken") -> bool:
        return literal.template_token_type == TokenType.Number

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        pass
