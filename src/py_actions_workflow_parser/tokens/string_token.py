"""StringToken — a string literal value."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .literal_token import LiteralToken
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class StringToken(LiteralToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        value: str,
        definition_info: "DefinitionInfo | None",
        source: str | None = None,
        block_scalar_header: str | None = None,
    ) -> None:
        super().__init__(TokenType.String, file, range, definition_info)
        self.value = value
        self.source = source
        self.block_scalar_header = block_scalar_header

    def clone(self, omit_source: bool = False) -> TemplateToken:
        if omit_source:
            return StringToken(
                None,
                None,
                self.value,
                self.definition_info,
                self.source,
                self.block_scalar_header,
            )
        return StringToken(
            self.file,
            self.range,
            self.value,
            self.definition_info,
            self.source,
            self.block_scalar_header,
        )

    def __str__(self) -> str:
        return self.value

    def to_json(self) -> object:
        return self.value
