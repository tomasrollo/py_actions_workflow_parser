"""SequenceToken — an ordered list of TemplateTokens."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class SequenceToken(TemplateToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(TokenType.Sequence, file, range, definition_info)
        self._seq: list[TemplateToken] = []

    @property
    def count(self) -> int:
        return len(self._seq)

    @property
    def is_scalar(self) -> bool:
        return False

    @property
    def is_literal(self) -> bool:
        return False

    @property
    def is_expression(self) -> bool:
        return False

    def add(self, value: TemplateToken) -> None:
        self._seq.append(value)

    def get(self, index: int) -> TemplateToken:
        return self._seq[index]

    def clone(self, omit_source: bool = False) -> TemplateToken:
        result = (
            SequenceToken(None, None, self.definition_info)
            if omit_source
            else SequenceToken(self.file, self.range, self.definition_info)
        )
        for item in self._seq:
            result.add(item.clone(omit_source))
        return result

    def to_json(self) -> object:
        return {"type": int(TokenType.Sequence), "seq": self._seq}

    def __iter__(self) -> Iterator[TemplateToken]:
        return iter(self._seq)
