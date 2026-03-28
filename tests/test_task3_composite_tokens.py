"""Task 3 validation: composite and expression tokens, type guards."""

import pytest
from py_actions_expressions_parser import ExpressionError

from py_actions_workflow_parser.tokens.string_token import StringToken
from py_actions_workflow_parser.tokens.number_token import NumberToken
from py_actions_workflow_parser.tokens.sequence_token import SequenceToken
from py_actions_workflow_parser.tokens.mapping_token import MappingToken
from py_actions_workflow_parser.tokens.basic_expression_token import BasicExpressionToken
from py_actions_workflow_parser.tokens.insert_expression_token import InsertExpressionToken
from py_actions_workflow_parser.tokens.expression_token import ExpressionToken
from py_actions_workflow_parser.tokens.types import TokenType
from py_actions_workflow_parser.tokens.type_guards import (
    is_string, is_number, is_boolean, is_sequence, is_mapping,
    is_basic_expression, is_insert_expression, is_null,
)


def test_sequence_token():
    seq = SequenceToken(None, None, None)
    s1 = StringToken(None, None, "a", None)
    s2 = StringToken(None, None, "b", None)
    seq.add(s1)
    seq.add(s2)
    assert seq.count == 2
    assert seq.get(0) is s1
    assert seq.get(1) is s2
    assert seq.template_token_type == TokenType.Sequence
    assert not seq.is_scalar
    assert not seq.is_expression
    assert not seq.is_literal


def test_sequence_iteration():
    seq = SequenceToken(None, None, None)
    seq.add(StringToken(None, None, "x", None))
    seq.add(StringToken(None, None, "y", None))
    items = list(seq)
    assert len(items) == 2
    assert str(items[0]) == "x"


def test_sequence_clone():
    seq = SequenceToken(1, None, None)
    seq.add(StringToken(None, None, "x", None))
    c = seq.clone(omit_source=True)
    assert isinstance(c, SequenceToken)
    assert c.file is None
    assert c.count == 1


def test_mapping_token():
    m = MappingToken(None, None, None)
    k = StringToken(None, None, "key", None)
    v = StringToken(None, None, "val", None)
    m.add(k, v)
    assert m.count == 1
    assert m.get(0).key is k
    assert m.get(0).value is v
    assert m.template_token_type == TokenType.Mapping
    assert not m.is_scalar


def test_mapping_find():
    m = MappingToken(None, None, None)
    m.add(StringToken(None, None, "foo", None), StringToken(None, None, "bar", None))
    result = m.find("foo")
    assert result is not None
    assert str(result) == "bar"
    assert m.find("missing") is None


def test_mapping_iteration():
    m = MappingToken(None, None, None)
    m.add(StringToken(None, None, "k", None), StringToken(None, None, "v", None))
    pairs = list(m)
    assert len(pairs) == 1
    assert str(pairs[0].key) == "k"


def test_basic_expression_token():
    expr = BasicExpressionToken(None, None, "github.ref", None)
    assert expr.expression == "github.ref"
    assert expr.is_expression
    assert not expr.is_literal
    assert expr.template_token_type == TokenType.BasicExpression
    assert str(expr) == "${{ github.ref }}"


def test_insert_expression_token():
    t = InsertExpressionToken(None, None, None)
    assert t.directive == "insert"
    assert str(t) == "${{ insert }}"
    assert t.template_token_type == TokenType.InsertExpression


def test_validate_expression_valid():
    ExpressionToken.validate_expression("github.ref", ["github"])


def test_validate_expression_invalid():
    with pytest.raises(Exception):
        ExpressionToken.validate_expression("github.event = 12", ["github"])


def test_type_guards():
    s = StringToken(None, None, "x", None)
    n = NumberToken(None, None, 1.0, None)
    seq = SequenceToken(None, None, None)
    m = MappingToken(None, None, None)
    expr = BasicExpressionToken(None, None, "a", None)
    ins = InsertExpressionToken(None, None, None)

    assert is_string(s)
    assert not is_string(n)
    assert is_number(n)
    assert is_sequence(seq)
    assert is_mapping(m)
    assert is_basic_expression(expr)
    assert is_insert_expression(ins)
    assert not is_basic_expression(s)


def test_traverse_sequence():
    from py_actions_workflow_parser.tokens.template_token import TemplateToken as TT
    seq = SequenceToken(None, None, None)
    s1 = StringToken(None, None, "a", None)
    s2 = StringToken(None, None, "b", None)
    seq.add(s1)
    seq.add(s2)
    tokens = list(TT.traverse(seq))
    # root + 2 items
    assert len(tokens) == 3
    assert tokens[0][1] is seq
    values = {str(t[1]) for t in tokens[1:]}
    assert values == {"a", "b"}
