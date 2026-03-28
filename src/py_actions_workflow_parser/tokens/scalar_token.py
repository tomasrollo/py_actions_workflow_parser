"""ScalarToken abstract base — base for all non-container tokens."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class ScalarToken(TemplateToken):
    """Base class for everything that is not a mapping or sequence."""

    def __init__(
        self,
        token_type: TokenType,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(token_type, file, range, definition_info)

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def to_display_string(self) -> str: ...

    @property
    def is_scalar(self) -> bool:
        return True

    @staticmethod
    def _trim_display_string(display_string: str) -> str:
        first_line = display_string.lstrip()
        nl = first_line.find("\n")
        cr = first_line.find("\r")
        if nl >= 0 or cr >= 0:
            cut = min(
                nl if nl >= 0 else len(first_line),
                cr if cr >= 0 else len(first_line),
            )
            first_line = first_line[:cut]
        return first_line
