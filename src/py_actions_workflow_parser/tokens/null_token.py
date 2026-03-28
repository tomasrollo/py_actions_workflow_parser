"""NullToken — a null literal value."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .literal_token import LiteralToken
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class NullToken(LiteralToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(TokenType.Null, file, range, definition_info)

    def clone(self, omit_source: bool = False) -> TemplateToken:
        if omit_source:
            return NullToken(None, None, self.definition_info)
        return NullToken(self.file, self.range, self.definition_info)

    def __str__(self) -> str:
        return ""

    def to_json(self) -> object:
        return None
