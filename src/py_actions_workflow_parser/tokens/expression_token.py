"""ExpressionToken abstract base — scalar tokens containing ${{ }} expressions."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from py_actions_expressions_parser import Lexer, Parser, ExpressionError

from ..templates.allowed_context import split_allowed_context
from .scalar_token import ScalarToken
from .token_range import TokenRange
from .types import TokenType

if TYPE_CHECKING:
    from ..schema.definition_info import DefinitionInfo


class ExpressionToken(ScalarToken):

    def __init__(
        self,
        token_type: TokenType,
        file: int | None,
        range: TokenRange | None,
        directive: str | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        super().__init__(token_type, file, range, definition_info)
        self.directive = directive

    @property
    def is_literal(self) -> bool:
        return False

    @property
    def is_expression(self) -> bool:
        return True

    @staticmethod
    def validate_expression(expression: str, allowed_context: list[str]) -> None:
        """Validate an expression string against the allowed context.

        Raises ExpressionError or Exception if the expression is invalid.
        """
        named_contexts, functions = split_allowed_context(allowed_context)
        tokens = Lexer(expression).lex()
        Parser(tokens, named_contexts, functions).parse()
