"""StringDefinition — string type with optional constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import (
    CONSTANT,
    DEFINITION,
    IGNORE_CASE,
    IS_EXPRESSION,
    REQUIRE_NON_EMPTY,
    STRING,
)
from ..tokens.types import TokenType
from .definition_type import DefinitionType
from .scalar_definition import ScalarDefinition

if TYPE_CHECKING:
    from ..tokens.literal_token import LiteralToken
    from ..tokens.mapping_token import MappingToken
    from .template_schema import TemplateSchema


class StringDefinition(ScalarDefinition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)
        self.constant: str = ""
        self.ignore_case: bool = False
        self.require_non_empty: bool = False
        self.is_expression: bool = False

        if definition is not None:
            for pair in definition:
                dk = pair.key.assert_string(f"{DEFINITION} key")
                if dk.value == STRING:
                    mapping = pair.value.assert_mapping(f"{DEFINITION} {STRING}")
                    for mp in mapping:
                        mk = mp.key.assert_string(f"{DEFINITION} {STRING} key")
                        if mk.value == CONSTANT:
                            self.constant = mp.value.assert_string(
                                f"{DEFINITION} {STRING} {CONSTANT}"
                            ).value
                        elif mk.value == IGNORE_CASE:
                            self.ignore_case = mp.value.assert_boolean(
                                f"{DEFINITION} {STRING} {IGNORE_CASE}"
                            ).value
                        elif mk.value == REQUIRE_NON_EMPTY:
                            self.require_non_empty = mp.value.assert_boolean(
                                f"{DEFINITION} {STRING} {REQUIRE_NON_EMPTY}"
                            ).value
                        elif mk.value == IS_EXPRESSION:
                            self.is_expression = mp.value.assert_boolean(
                                f"{DEFINITION} {STRING} {IS_EXPRESSION}"
                            ).value
                        else:
                            mk.assert_unexpected_value(f"{DEFINITION} {STRING} key")
                else:
                    dk.assert_unexpected_value(f"{DEFINITION} key")

    @property
    def definition_type(self) -> DefinitionType:
        return DefinitionType.String

    def is_match(self, literal: "LiteralToken") -> bool:
        if literal.template_token_type == TokenType.String:
            from ..tokens.string_token import StringToken

            value = literal.assert_string("string match").value
            if self.constant:
                if self.ignore_case:
                    return self.constant.upper() == value.upper()
                return self.constant == value
            elif self.require_non_empty:
                return bool(value)
            else:
                return True
        return False

    def validate(self, schema: "TemplateSchema", name: str) -> None:
        if self.constant and self.require_non_empty:
            raise ValueError(
                f"Properties '{CONSTANT}' and '{REQUIRE_NON_EMPTY}' cannot both be set"
            )
