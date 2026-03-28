"""TemplateParseResult — result of parsing a template file."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .template_context import TemplateContext
    from .tokens.template_token import TemplateToken


class TemplateParseResult:
    __slots__ = ("context", "value")

    def __init__(
        self,
        context: "TemplateContext",
        value: "TemplateToken | None",
    ) -> None:
        self.context = context
        self.value = value
