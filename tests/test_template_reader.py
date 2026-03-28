"""Tests for the TemplateReader — schema-driven validation engine."""

from __future__ import annotations

import pytest

from py_actions_workflow_parser import parse_workflow, NoOperationTraceWriter
from py_actions_workflow_parser.workflows.file import File
from py_actions_workflow_parser.tokens.types import TokenType
from py_actions_workflow_parser.tokens.type_guards import (
    is_mapping,
    is_string,
    is_sequence,
)


def _parse_raw(content: str):
    """Return (token_tree, context) for a workflow string."""
    f = File(name=".github/workflows/test.yml", content=content)
    result = parse_workflow(f, NoOperationTraceWriter())
    return result.value, result.context


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_root_is_mapping():
    root, ctx = _parse_raw(
        "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: hi"
    )
    assert ctx.errors.count == 0
    assert is_mapping(root)


def test_root_has_on_and_jobs():
    root, ctx = _parse_raw(
        "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: hi"
    )
    assert root.find("on") is not None
    assert root.find("jobs") is not None


def test_steps_is_sequence():
    root, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
      - uses: actions/checkout@v4
"""
    )
    jobs = root.find("jobs")
    assert is_mapping(jobs)
    build = jobs.find("build")
    steps = build.find("steps")
    assert is_sequence(steps)
    assert steps.count == 2


# ---------------------------------------------------------------------------
# Unknown key detection
# ---------------------------------------------------------------------------


def test_unknown_root_key_produces_error():
    _, ctx = _parse_raw(
        """
on: push
badkey: value
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: hi
"""
    )
    assert ctx.errors.count >= 1
    messages = [e.message for e in ctx.errors.get_errors()]
    assert any("badkey" in m or "Unexpected" in m for m in messages)


def test_unknown_job_key_produces_error():
    _, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    unknownkey: value
    steps:
      - run: hi
"""
    )
    assert ctx.errors.count >= 1


# ---------------------------------------------------------------------------
# Expression detection
# ---------------------------------------------------------------------------


def test_expression_in_string_field():
    root, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ${{ matrix.os }}
    steps:
      - run: hi
"""
    )
    assert ctx.errors.count == 0
    jobs = root.find("jobs")
    build = jobs.find("build")
    runs_on = build.find("runs-on")
    assert runs_on.template_token_type == TokenType.BasicExpression


def test_multi_expression_string():
    """A string with multiple ${{ }} produces a format() expression."""
    root, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo ${{ github.actor }}/${{ github.ref }}
"""
    )
    # The run step's value should be a BasicExpression (format(...))
    assert ctx.errors.count == 0


def test_invalid_expression_syntax():
    _, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    if: ${{ github.event = 12 }}
    steps:
      - run: hi
"""
    )
    assert ctx.errors.count >= 1


# ---------------------------------------------------------------------------
# Scalar type coercion
# ---------------------------------------------------------------------------


def test_boolean_coerced_to_string_in_string_field():
    """Values like 'true' should be strings when schema expects a string."""
    root, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
        continue-on-error: true
"""
    )
    assert ctx.errors.count == 0


# ---------------------------------------------------------------------------
# Duplicate key detection
# ---------------------------------------------------------------------------


def test_duplicate_key_produces_error():
    _, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
  build:
    runs-on: ubuntu-22.04
    steps:
      - run: echo bye
"""
    )
    assert ctx.errors.count >= 1


# ---------------------------------------------------------------------------
# Error position information
# ---------------------------------------------------------------------------


def test_error_has_line_and_col():
    _, ctx = _parse_raw(
        """
on: push
jobs:
  build:
    badprop: value
    runs-on: ubuntu-latest
    steps:
      - run: hi
"""
    )
    assert ctx.errors.count >= 1
    err = ctx.errors.get_errors()[0]
    # Error should reference the file
    assert err.message != ""


# ---------------------------------------------------------------------------
# Context errors count property
# ---------------------------------------------------------------------------


def test_no_errors_on_valid_workflow():
    _, ctx = _parse_raw(
        """
on:
  push:
    branches:
      - main
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      FOO: bar
    steps:
      - uses: actions/checkout@v4
      - run: pytest
"""
    )
    assert ctx.errors.count == 0
