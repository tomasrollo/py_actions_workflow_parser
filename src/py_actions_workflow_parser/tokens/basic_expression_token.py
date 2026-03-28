"""BasicExpressionToken — a ${{ expression }} token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..templates.template_constants import OPEN_EXPRESSION, CLOSE_EXPRESSION
from .expression_token import ExpressionToken
from .scalar_token import ScalarToken
from .template_token import TemplateToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class BasicExpressionToken(ExpressionToken):

    def __init__(
        self,
        file: int | None,
        range: TokenRange | None,
        expression: str,
        definition_info: "DefinitionInfo | None",
        original_expressions: "list[BasicExpressionToken] | None" = None,
        source: str | None = None,
        expression_range: TokenRange | None = None,
        block_scalar_header: str | None = None,
    ) -> None:
        super().__init__(TokenType.BasicExpression, file, range, None, definition_info)
        self._expr = expression
        self.source = source
        self.original_expressions = original_expressions
        self.expression_range = expression_range
        self.block_scalar_header = block_scalar_header

    @property
    def expression(self) -> str:
        return self._expr

    def clone(self, omit_source: bool = False) -> TemplateToken:
        if omit_source:
            return BasicExpressionToken(
                None,
                None,
                self._expr,
                self.definition_info,
                self.original_expressions,
                self.source,
                self.expression_range,
                self.block_scalar_header,
            )
        return BasicExpressionToken(
            self.file,
            self.range,
            self._expr,
            self.definition_info,
            self.original_expressions,
            self.source,
            self.expression_range,
            self.block_scalar_header,
        )

    def __str__(self) -> str:
        return f"{OPEN_EXPRESSION} {self._expr} {CLOSE_EXPRESSION}"

    def to_display_string(self) -> str:
        return ScalarToken._trim_display_string(str(self))

    def to_json(self) -> object:
        return {"type": int(TokenType.BasicExpression), "expr": self._expr}
