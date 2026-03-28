"""ObjectReader protocol — abstract interface for reading a source object or file."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens.literal_token import LiteralToken
    from ..tokens.mapping_token import MappingToken
    from ..tokens.sequence_token import SequenceToken


class ObjectReader(ABC):
    """Interface for reading a source object (or file).

    Used by TemplateReader to build a TemplateToken DOM.
    """

    @abstractmethod
    def allow_literal(self) -> "LiteralToken | None": ...

    @abstractmethod
    def allow_sequence_start(self) -> "SequenceToken | None": ...

    @abstractmethod
    def allow_sequence_end(self) -> bool: ...

    @abstractmethod
    def allow_mapping_start(self) -> "MappingToken | None": ...

    @abstractmethod
    def allow_mapping_end(self) -> bool: ...

    @abstractmethod
    def validate_start(self) -> None: ...

    @abstractmethod
    def validate_end(self) -> None: ...
