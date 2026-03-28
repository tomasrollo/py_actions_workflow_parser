"""LiteralToken abstract base — non-expression scalar tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .scalar_token import ScalarToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class LiteralToken(ScalarToken):

    def __init__(
        self,
        token_type: TokenType,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(token_type, file, range, definition_info)

    @property
    def is_literal(self) -> bool:
        return True

    @property
    def is_expression(self) -> bool:
        return False

    def to_display_string(self) -> str:
        return ScalarToken._trim_display_string(str(self))

    def assert_unexpected_value(self, object_description: str) -> None:
        raise ValueError(
            f"Error while reading '{object_description}'. Unexpected value '{str(self)}'"
        )
