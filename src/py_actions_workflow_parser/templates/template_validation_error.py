"""TemplateValidationError — a single validation error with prefix and range."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens.token_range import TokenRange


class TemplateValidationError:
    def __init__(
        self,
        raw_message: str,
        prefix: str | None,
        code: str | None,
        range: "TokenRange | None",
    ) -> None:
        self.raw_message = raw_message
        self.prefix = prefix
        self.code = code
        self.range = range

    @property
    def message(self) -> str:
        if self.prefix:
            return f"{self.prefix}: {self.raw_message}"
        return self.raw_message

    def __str__(self) -> str:
        return self.message
