"""ScalarDefinition abstract base — base for all scalar type definitions."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from .definition import Definition

if TYPE_CHECKING:
    from ..tokens.literal_token import LiteralToken
    from ..tokens.mapping_token import MappingToken


class ScalarDefinition(Definition):

    def __init__(self, key: str, definition: "MappingToken | None" = None) -> None:
        super().__init__(key, definition)

    @abstractmethod
    def is_match(self, literal: "LiteralToken") -> bool: ...
