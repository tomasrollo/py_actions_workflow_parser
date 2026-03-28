"""convert_to_if_condition — ensures if-conditions contain a status function call."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from py_actions_expressions_parser import (  # type: ignore[import]
    Binary,
    FunctionInfo,
    Grouping,
    IndexAccess,
    Lexer,
    Logical,
    Parser,
    Unary,
    FunctionCall,
)

from ...templates.allowed_context import split_allowed_context
from ...templates.template_constants import OPEN_EXPRESSION, CLOSE_EXPRESSION
from ...tokens.basic_expression_token import BasicExpressionToken
from ...tokens.expression_token import ExpressionToken
from ...tokens.template_token import TemplateToken

if TYPE_CHECKING:
    from ...schema.definition_info import DefinitionInfo
    from ...templates.template_context import TemplateContext

_STATUS_FUNCS = {"success", "failure", "cancelled", "always"}

# Always available status functions (must be provided to the parser)
_STATUS_FUNCTION_INFOS = [
    FunctionInfo("success", 0, 0),
    FunctionInfo("failure", 0, 0),
    FunctionInfo("cancelled", 0, 0),
    FunctionInfo("always", 0, 0),
]


def walk_tree_to_find_status_function_calls(tree: object) -> bool:
    """Recursively check an expression AST for any status function call."""
    if tree is None:
        return False

    if isinstance(tree, FunctionCall):
        name = getattr(tree.function_name, "lexeme", "").lower()
        if name in _STATUS_FUNCS:
            return True
        args = getattr(tree, "args", [])
        return any(walk_tree_to_find_status_function_calls(a) for a in args)

    if isinstance(tree, Binary):
        return walk_tree_to_find_status_function_calls(
            tree.left
        ) or walk_tree_to_find_status_function_calls(tree.right)

    if isinstance(tree, Unary):
        return walk_tree_to_find_status_function_calls(getattr(tree, "expr", None))

    if isinstance(tree, Logical):
        args = getattr(tree, "args", [])
        return any(walk_tree_to_find_status_function_calls(a) for a in args)

    if isinstance(tree, Grouping):
        return walk_tree_to_find_status_function_calls(getattr(tree, "group", None))

    if isinstance(tree, IndexAccess):
        return walk_tree_to_find_status_function_calls(
            getattr(tree, "expr", None)
        ) or walk_tree_to_find_status_function_calls(getattr(tree, "index", None))

    return False


def ensure_status_function(
    condition: str,
    definition_info: "DefinitionInfo | None",
) -> str:
    """Wrap condition in `success() && (...)` if no status function is present."""
    allowed_context = definition_info.allowed_context if definition_info else []
    try:
        named_contexts, functions = split_allowed_context(allowed_context)
        # Always include the status functions so the parser recognises them
        all_funcs = list(functions) + _STATUS_FUNCTION_INFOS
        tokens = Lexer(condition).lex()
        tree = Parser(tokens, named_contexts, all_funcs).parse()
        if walk_tree_to_find_status_function_calls(tree):
            return condition
        return f"success() && ({condition})"
    except Exception:
        return condition


def convert_to_if_condition(
    context: "TemplateContext",
    token: TemplateToken,
) -> Optional[BasicExpressionToken]:
    """Convert an if-condition token to a BasicExpressionToken."""
    scalar = token.assert_scalar("if condition")
    allowed_context = (
        token.definition_info.allowed_context if token.definition_info else []
    )

    if isinstance(scalar, BasicExpressionToken):
        condition = scalar.expression
        source = scalar.source
    else:
        string_token = scalar.assert_string("if condition")
        condition = string_token.value.strip()
        source = string_token.source

    if not condition:
        final_condition = "success()"
    else:
        final_condition = ensure_status_function(condition, token.definition_info)

    try:
        ExpressionToken.validate_expression(final_condition, allowed_context)
    except Exception as err:
        context.error(token, err)
        return None

    return BasicExpressionToken(
        token.file, token.range, final_condition, token.definition_info, None, source
    )


def validate_runs_if_condition(
    context: "TemplateContext",
    token: TemplateToken,
    condition: str,
) -> Optional[str]:
    """Validate a pre-if or post-if condition string (no wrapping)."""
    allowed_context = (
        token.definition_info.allowed_context if token.definition_info else []
    )
    try:
        ExpressionToken.validate_expression(condition, allowed_context)
    except Exception as err:
        context.error(token, err)
        return None
    return condition
