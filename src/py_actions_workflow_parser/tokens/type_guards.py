"""Type guard functions for TemplateToken subtypes."""

from __future__ import annotations

from .basic_expression_token import BasicExpressionToken
from .boolean_token import BooleanToken
from .literal_token import LiteralToken
from .mapping_token import MappingToken
from .number_token import NumberToken
from .scalar_token import ScalarToken
from .sequence_token import SequenceToken
from .string_token import StringToken
from .template_token import TemplateToken
from .types import TokenType


def is_literal(t: TemplateToken) -> bool:
    return t.is_literal


def is_scalar(t: TemplateToken) -> bool:
    return t.is_scalar


def is_string(t: TemplateToken) -> bool:
    return t.is_literal and t.template_token_type == TokenType.String


def is_number(t: TemplateToken) -> bool:
    return t.is_literal and t.template_token_type == TokenType.Number


def is_boolean(t: TemplateToken) -> bool:
    return t.is_literal and t.template_token_type == TokenType.Boolean


def is_null(t: TemplateToken) -> bool:
    return t.is_literal and t.template_token_type == TokenType.Null


def is_basic_expression(t: TemplateToken) -> bool:
    return t.is_scalar and t.template_token_type == TokenType.BasicExpression


def is_insert_expression(t: TemplateToken) -> bool:
    return t.is_scalar and t.template_token_type == TokenType.InsertExpression


def is_sequence(t: TemplateToken) -> bool:
    return isinstance(t, SequenceToken)


def is_mapping(t: TemplateToken) -> bool:
    return isinstance(t, MappingToken)
