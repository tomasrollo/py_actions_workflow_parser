"""BooleanToken — a boolean literal value."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .literal_token import LiteralToken
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class BooleanToken(LiteralToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        value: bool,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(TokenType.Boolean, file, range, definition_info)
        self._value = value

    @property
    def value(self) -> bool:
        return self._value

    def clone(self, omit_source: bool = False) -> TemplateToken:
        if omit_source:
            return BooleanToken(None, None, self._value, self.definition_info)
        return BooleanToken(self.file, self.range, self._value, self.definition_info)

    def __str__(self) -> str:
        return "true" if self._value else "false"

    def to_json(self) -> object:
        return self._value
