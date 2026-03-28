"""Task 2 validation: token base classes and literal tokens."""

import pytest
from py_actions_workflow_parser.tokens.string_token import StringToken
from py_actions_workflow_parser.tokens.number_token import NumberToken
from py_actions_workflow_parser.tokens.boolean_token import BooleanToken
from py_actions_workflow_parser.tokens.null_token import NullToken
from py_actions_workflow_parser.tokens.key_value_pair import KeyValuePair
from py_actions_workflow_parser.tokens.types import TokenType


def test_string_token():
    s = StringToken(1, None, "hello", None)
    assert s.value == "hello"
    assert str(s) == "hello"
    assert s.is_literal
    assert not s.is_expression
    assert s.is_scalar
    assert s.template_token_type == TokenType.String


def test_number_token():
    n = NumberToken(None, None, 42.0, None)
    assert n.value == 42.0
    assert str(n) == "42"
    assert n.template_token_type == TokenType.Number


def test_boolean_token():
    b = BooleanToken(None, None, True, None)
    assert b.value is True
    assert str(b) == "true"
    bf = BooleanToken(None, None, False, None)
    assert str(bf) == "false"


def test_null_token():
    nu = NullToken(None, None, None)
    assert str(nu) == ""
    assert nu.to_json() is None
    assert nu.template_token_type == TokenType.Null


def test_key_value_pair():
    s = StringToken(1, None, "key", None)
    n = NumberToken(None, None, 1.0, None)
    kv = KeyValuePair(s, n)
    assert kv.key is s
    assert kv.value is n


def test_clone_with_source():
    s = StringToken(1, None, "hello", None)
    s2 = s.clone(omit_source=False)
    assert s2.value == "hello"
    assert s2.file == 1


def test_clone_omit_source():
    s = StringToken(1, None, "hello", None)
    s3 = s.clone(omit_source=True)
    assert s3.file is None


def test_assert_methods():
    s = StringToken(None, None, "x", None)
    assert s.assert_string("test") is s
    with pytest.raises(Exception):
        s.assert_number("test")
