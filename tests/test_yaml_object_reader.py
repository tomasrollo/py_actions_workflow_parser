"""Tests for YamlObjectReader — YAML to ParseEvent stream."""

from __future__ import annotations

from py_actions_workflow_parser.templates.parse_event import EventType
from py_actions_workflow_parser.workflows.yaml_object_reader import YamlObjectReader
from py_actions_workflow_parser.tokens.types import TokenType


def _events(content: str) -> list:
    reader = YamlObjectReader(file_id=1, content=content)
    reader.validate_start()
    events = []
    while True:
        e = reader.allow_literal()
        if e is not None:
            events.append(("literal", e))
            continue
        e = reader.allow_sequence_start()
        if e is not None:
            events.append(("seq_start",))
            continue
        if reader.allow_sequence_end():
            events.append(("seq_end",))
            continue
        e = reader.allow_mapping_start()
        if e is not None:
            events.append(("map_start",))
            continue
        if reader.allow_mapping_end():
            events.append(("map_end",))
            continue
        break
    return events


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------


def test_string_scalar():
    reader = YamlObjectReader(1, "value: hello")
    reader.validate_start()
    reader.allow_mapping_start()
    key = reader.allow_literal()
    val = reader.allow_literal()
    assert key.value == "value"
    assert val.value == "hello"
    assert val.template_token_type == TokenType.String


def test_integer_scalar():
    reader = YamlObjectReader(1, "value: 42")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()  # key
    val = reader.allow_literal()
    assert val.template_token_type == TokenType.Number
    assert val.value == 42


def test_boolean_scalar():
    reader = YamlObjectReader(1, "value: true")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    assert val.template_token_type == TokenType.Boolean
    assert val.value is True


def test_null_scalar():
    reader = YamlObjectReader(1, "value: ~")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    assert val.template_token_type == TokenType.Null


def test_implicit_null():
    """'key:' with no value should produce a Null token."""
    reader = YamlObjectReader(1, "key:")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()  # key
    val = reader.allow_literal()
    assert val.template_token_type == TokenType.Null


def test_sequence():
    reader = YamlObjectReader(1, "items:\n  - a\n  - b")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()  # key "items"
    seq = reader.allow_sequence_start()
    assert seq is not None
    a = reader.allow_literal()
    b = reader.allow_literal()
    assert a.value == "a"
    assert b.value == "b"
    assert reader.allow_sequence_end()


def test_nested_mapping():
    reader = YamlObjectReader(1, "outer:\n  inner: value")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()  # "outer"
    reader.allow_mapping_start()
    key = reader.allow_literal()
    val = reader.allow_literal()
    assert key.value == "inner"
    assert val.value == "value"


# ---------------------------------------------------------------------------
# Source positions
# ---------------------------------------------------------------------------


def test_position_line_col():
    reader = YamlObjectReader(1, "key: value\n")
    reader.validate_start()
    reader.allow_mapping_start()
    key_tok = reader.allow_literal()
    assert key_tok.range is not None
    assert key_tok.range.start.line == 1
    assert key_tok.range.start.column == 1


def test_value_position():
    reader = YamlObjectReader(1, "key: hello\n")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()  # key
    val_tok = reader.allow_literal()
    assert val_tok.range is not None
    assert val_tok.range.start.line == 1
    assert val_tok.range.start.column == 6


def test_implicit_null_position_after_colon():
    """Null value for 'image:' should be positioned right after the ':'."""
    reader = YamlObjectReader(1, "image:\n")
    reader.validate_start()
    reader.allow_mapping_start()
    key_tok = reader.allow_literal()
    val_tok = reader.allow_literal()
    assert val_tok.template_token_type == TokenType.Null
    # Should be on line 1, right after "image:" (col 7)
    assert val_tok.range is not None
    assert val_tok.range.start.line == 1
    assert val_tok.range.start.column == 7


# ---------------------------------------------------------------------------
# Block scalars
# ---------------------------------------------------------------------------


def test_literal_block_scalar():
    yaml = "value: |\n  Line 1\n  Line 2\n"
    reader = YamlObjectReader(1, yaml)
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    assert val.value == "Line 1\nLine 2\n"


def test_folded_block_scalar():
    yaml = "value: >\n  Line 1\n  Line 2\n"
    reader = YamlObjectReader(1, yaml)
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    # Folded: newlines become spaces within a paragraph
    assert val.value == "Line 1 Line 2\n"


def test_block_scalar_strip():
    yaml = "value: |-\n  hello\n"
    reader = YamlObjectReader(1, yaml)
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    assert val.value == "hello"


# ---------------------------------------------------------------------------
# YAML 1.2 behaviour
# ---------------------------------------------------------------------------


def test_underscored_int_is_string():
    """YAML 1.2 core schema does not treat 12_345 as an integer."""
    reader = YamlObjectReader(1, "value: 12_345")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    assert val.template_token_type == TokenType.String
    assert val.value == "12_345"


def test_underscored_float_is_string():
    reader = YamlObjectReader(1, "value: 1_234.5")
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()
    val = reader.allow_literal()
    assert val.template_token_type == TokenType.String


# ---------------------------------------------------------------------------
# YAML aliases
# ---------------------------------------------------------------------------


def test_alias_resolution():
    yaml = "anchor: &a hello\nalias: *a\n"
    reader = YamlObjectReader(1, yaml)
    reader.validate_start()
    reader.allow_mapping_start()
    reader.allow_literal()  # "anchor"
    anchor_val = reader.allow_literal()
    reader.allow_literal()  # "alias"
    alias_val = reader.allow_literal()
    assert anchor_val.value == "hello"
    assert alias_val.value == "hello"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_invalid_yaml_populates_errors():
    reader = YamlObjectReader(1, "key: [\n")
    assert len(reader.errors) >= 1
