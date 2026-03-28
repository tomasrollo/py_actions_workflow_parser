"""MappingToken — an ordered collection of key-value pairs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from .key_value_pair import KeyValuePair
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo
    from .scalar_token import ScalarToken


class MappingToken(TemplateToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(TokenType.Mapping, file, range, definition_info)
        self._map: list[KeyValuePair] = []

    @property
    def count(self) -> int:
        return len(self._map)

    @property
    def is_scalar(self) -> bool:
        return False

    @property
    def is_literal(self) -> bool:
        return False

    @property
    def is_expression(self) -> bool:
        return False

    def add(self, key: "ScalarToken", value: TemplateToken) -> None:
        self._map.append(KeyValuePair(key, value))

    def get(self, index: int) -> KeyValuePair:
        return self._map[index]

    def find(self, key: str) -> TemplateToken | None:
        for pair in self._map:
            if str(pair.key) == key:
                return pair.value
        return None

    def remove(self, index: int) -> None:
        del self._map[index]

    def clone(self, omit_source: bool = False) -> TemplateToken:
        from .scalar_token import ScalarToken as SC
        result = (
            MappingToken(None, None, self.definition_info)
            if omit_source
            else MappingToken(self.file, self.range, self.definition_info)
        )
        for item in self._map:
            result.add(
                item.key.clone(omit_source),  # type: ignore[arg-type]
                item.value.clone(omit_source),
            )
        return result

    def to_json(self) -> object:
        items = [{"Key": pair.key, "Value": pair.value} for pair in self._map]
        return {"type": int(TokenType.Mapping), "map": items}

    def __iter__(self) -> Iterator[KeyValuePair]:
        return iter(self._map)
