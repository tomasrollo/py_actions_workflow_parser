"""PropertyDefinition — metadata for a single mapping property."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import (
    DESCRIPTION,
    MAPPING_PROPERTY_VALUE,
    REQUIRED,
    TYPE,
)
from ..tokens.types import TokenType

if TYPE_CHECKING:
    from ..tokens.template_token import TemplateToken


class PropertyDefinition:

    def __init__(self, token: "TemplateToken") -> None:
        self.type: str = ""
        self.required: bool = False
        self.description: str | None = None

        if token.template_token_type == TokenType.String:
            from ..tokens.string_token import StringToken

            self.type = token.assert_string(MAPPING_PROPERTY_VALUE).value  # type: ignore[arg-type]
        else:
            mapping = token.assert_mapping(MAPPING_PROPERTY_VALUE)
            for pair in mapping:
                key = pair.key.assert_string(f"{MAPPING_PROPERTY_VALUE} key")
                if key.value == TYPE:
                    self.type = pair.value.assert_string(
                        f"{MAPPING_PROPERTY_VALUE} {TYPE}"
                    ).value
                elif key.value == REQUIRED:
                    self.required = pair.value.assert_boolean(
                        f"{MAPPING_PROPERTY_VALUE} {REQUIRED}"
                    ).value
                elif key.value == DESCRIPTION:
                    self.description = pair.value.assert_string(
                        f"{MAPPING_PROPERTY_VALUE} {DESCRIPTION}"
                    ).value
                else:
                    key.assert_unexpected_value(f"{MAPPING_PROPERTY_VALUE} key")
