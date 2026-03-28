"""NumberToken — a numeric literal value."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .literal_token import LiteralToken
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class NumberToken(LiteralToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        value: float,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(TokenType.Number, file, range, definition_info)
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def clone(self, omit_source: bool = False) -> TemplateToken:
        if omit_source:
            return NumberToken(None, None, self._value, self.definition_info)
        return NumberToken(self.file, self.range, self._value, self.definition_info)

    def __str__(self) -> str:
        # Preserve integer representation when possible
        if self._value == int(self._value) and not (
            self._value != self._value
        ):  # not NaN
            return str(int(self._value))
        return str(self._value)

    def to_json(self) -> object:
        return self._value
