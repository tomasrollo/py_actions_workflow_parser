"""InsertExpressionToken — represents ${{ insert }} directive tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import (
    INSERT_DIRECTIVE,
    OPEN_EXPRESSION,
    CLOSE_EXPRESSION,
)
from .expression_token import ExpressionToken
from .scalar_token import ScalarToken
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class InsertExpressionToken(ExpressionToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(
            TokenType.InsertExpression, file, range, INSERT_DIRECTIVE, definition_info
        )

    def clone(self, omit_source: bool = False) -> TemplateToken:
        if omit_source:
            return InsertExpressionToken(None, None, self.definition_info)
        return InsertExpressionToken(self.file, self.range, self.definition_info)

    def __str__(self) -> str:
        return f"{OPEN_EXPRESSION} {INSERT_DIRECTIVE} {CLOSE_EXPRESSION}"

    def to_display_string(self) -> str:
        return ScalarToken._trim_display_string(str(self))

    def to_json(self) -> object:
        return {"type": int(TokenType.InsertExpression), "expr": INSERT_DIRECTIVE}
