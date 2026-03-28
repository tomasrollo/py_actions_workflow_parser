"""
Parametrized fixture test suite — runs every .yml file in testdata/reader/.

Each fixture file contains three --- -separated YAML documents:
  doc[0]: test options   (skip lists, include-source flag)
  doc[1]: workflow YAML  (the input to parse)
  doc[-1]: expected JSON (what the serializer must produce)

Tests in skipped-tests.txt are marked xfail.
Tests tagged skip:Python or relying on source-info are marked skip.
"""

from __future__ import annotations

import json

import pytest

from py_actions_workflow_parser import (
    convert_workflow_template,
    parse_workflow,
    NoOperationTraceWriter,
)
from py_actions_workflow_parser.model.serialize import workflow_template_to_json
from py_actions_workflow_parser.workflows.file import File

from conftest import WorkflowFixture, load_workflow_fixtures

_FIXTURE_PARAMS = load_workflow_fixtures()


@pytest.mark.parametrize("fixture", _FIXTURE_PARAMS)
def test_workflow_fixture(fixture: WorkflowFixture) -> None:
    """Parse, convert, and serialize a workflow; compare against expected JSON."""
    test_name = ".github/workflows/" + fixture.name
    f = File(name=test_name, content=fixture.workflow_yaml)

    result = parse_workflow(f, NoOperationTraceWriter())
    wt = convert_workflow_template(result.context, result.value)
    actual_json = workflow_template_to_json(wt, include_events=fixture.include_events)
    actual_dict = json.loads(actual_json)

    # Match TS test behaviour: if there are errors, omit jobs from comparison
    expected = dict(fixture.expected_dict)
    if "errors" in actual_dict:
        actual_dict.pop("jobs", None)
    if "errors" in expected:
        expected.pop("jobs", None)

    assert actual_dict == expected
