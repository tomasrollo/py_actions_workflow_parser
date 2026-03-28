"""Integration tests for parse_workflow() and convert_workflow_template()."""

from __future__ import annotations

import pytest

from py_actions_workflow_parser import (
    convert_workflow_template,
    parse_workflow,
    NoOperationTraceWriter,
    WorkflowTemplateConverterOptions,
    ErrorPolicy,
    is_string,
    is_basic_expression,
)
from py_actions_workflow_parser.model.type_guards import is_run_step, is_action_step
from py_actions_workflow_parser.workflows.file import File


def _parse(content: str) -> tuple:
    """Helper: parse + convert, return (wt, errors)."""
    f = File(name=".github/workflows/test.yml", content=content)
    result = parse_workflow(f, NoOperationTraceWriter())
    errors = result.context.errors.get_errors()
    wt = convert_workflow_template(result.context, result.value)
    return wt, errors


# ---------------------------------------------------------------------------
# Milestone 1: parse a minimal workflow
# ---------------------------------------------------------------------------


def test_minimal_workflow_no_errors():
    f = File(
        name="test.yml",
        content="on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi",
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    assert result.value is not None
    assert result.context.errors.count == 0


def test_convert_single_job():
    wt, errors = _parse(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo hi
"""
    )
    assert len(errors) == 0
    assert len(wt.jobs) == 1
    assert wt.jobs[0].id.value == "build"
    assert len(wt.jobs[0].steps) == 2


def test_step_types():
    wt, _ = _parse(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo hi
"""
    )
    steps = wt.jobs[0].steps
    assert is_action_step(steps[0])
    assert steps[0].uses.value == "actions/checkout@v4"
    assert is_run_step(steps[1])


def test_step_auto_ids():
    wt, _ = _parse(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo one
      - run: echo two
      - run: echo three
"""
    )
    ids = [s.id for s in wt.jobs[0].steps]
    assert ids[0] == "__run"
    assert ids[1] == "__run_2"
    assert ids[2] == "__run_3"


def test_step_explicit_id():
    wt, _ = _parse(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - id: my-step
        run: echo hi
"""
    )
    assert wt.jobs[0].steps[0].id == "my-step"


# ---------------------------------------------------------------------------
# Milestone 2: expression validation
# ---------------------------------------------------------------------------


def test_valid_expression_no_errors():
    f = File(
        name="test.yml",
        content="""
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    if: ${{ github.ref == 'refs/heads/main' }}
    steps:
      - run: echo hi
""",
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    assert result.context.errors.count == 0


def test_invalid_expression_produces_error():
    f = File(
        name="bad.yml",
        content="""
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    if: ${{ github.event = 12 }}
    steps:
      - run: echo hi
""",
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    assert result.context.errors.count >= 1


def test_if_condition_wrapped_with_success():
    wt, _ = _parse(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    if: github.ref == 'main'
    steps:
      - run: echo hi
"""
    )
    job = wt.jobs[0]
    assert job.if_condition is not None
    expr = job.if_condition.expression
    assert "success()" in expr


def test_if_condition_status_function_not_wrapped():
    wt, _ = _parse(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    if: failure()
    steps:
      - run: echo hi
"""
    )
    job = wt.jobs[0]
    assert job.if_condition.expression == "failure()"


# ---------------------------------------------------------------------------
# Milestone 3: full conversion
# ---------------------------------------------------------------------------


def test_job_needs_dependency():
    wt, errors = _parse(
        """
on: push
jobs:
  job_a:
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  job_b:
    needs: job_a
    runs-on: ubuntu-latest
    steps:
      - run: echo b
"""
    )
    assert len(errors) == 0
    job_b = next(j for j in wt.jobs if j.id.value == "job_b")
    assert job_b.needs is not None
    assert job_b.needs[0].value == "job_a"


def test_circular_needs_produces_error():
    f = File(
        name="circular.yml",
        content="""
on: push
jobs:
  a:
    needs: b
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  b:
    needs: a
    runs-on: ubuntu-latest
    steps:
      - run: echo b
""",
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    wt = convert_workflow_template(result.context, result.value)
    assert wt.errors or result.context.errors.count > 0


def test_events_push():
    wt, _ = _parse(
        "on: push\njobs:\n  b:\n    runs-on: ubuntu-latest\n    steps:\n      - run: hi"
    )
    assert wt.events is not None
    assert "push" in wt.events.event_order


def test_events_workflow_dispatch_inputs():
    wt, _ = _parse(
        """
on:
  workflow_dispatch:
    inputs:
      name:
        type: string
        required: true
jobs:
  b:
    runs-on: ubuntu-latest
    steps:
      - run: hi
"""
    )
    assert wt.events.workflow_dispatch is not None
    assert "name" in wt.events.workflow_dispatch.inputs


def test_workflow_level_env():
    wt, _ = _parse(
        """
on: push
env:
  MY_VAR: hello
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo $MY_VAR
"""
    )
    assert wt.env is not None


def test_error_policy_try_conversion():
    f = File(
        name="bad.yml",
        content="""
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    if: ${{ github.event = 12 }}
    steps:
      - run: echo hi
""",
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    opts = WorkflowTemplateConverterOptions(error_policy=ErrorPolicy.TryConversion)
    wt = convert_workflow_template(result.context, result.value, options=opts)
    # With TryConversion, jobs are still populated
    assert len(wt.jobs) >= 1


# ---------------------------------------------------------------------------
# Error message formatting
# ---------------------------------------------------------------------------


def test_error_has_location():
    f = File(
        name=".github/workflows/bad.yml",
        content="on: push\njobs:\n  build:\n    badkey: value\n    runs-on: ubuntu-latest\n    steps:\n      - run: hi",
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    assert result.context.errors.count >= 1
    err = result.context.errors.get_errors()[0]
    assert err.message != ""


def test_invalid_yaml_reports_error():
    f = File(
        name="test.yml",
        content="on: push\njobs:\n  build: [\n",  # unclosed bracket — invalid YAML
    )
    result = parse_workflow(f, NoOperationTraceWriter())
    assert result.context.errors.count >= 1
    assert result.value is None
