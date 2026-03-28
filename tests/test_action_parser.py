"""Tests for parse_action() and convert_action_template()."""

from __future__ import annotations

import pytest

from py_actions_workflow_parser import (
    parse_action,
    convert_action_template,
    NoOperationTraceWriter,
    ActionTemplate,
    ActionRunsComposite,
    ActionRunsNode,
    ActionRunsDocker,
)
from py_actions_workflow_parser.workflows.file import File


def _parse(content: str) -> tuple[ActionTemplate, list]:
    f = File(name="action.yml", content=content)
    result = parse_action(f, NoOperationTraceWriter())
    errors = result.context.errors.get_errors()
    at = convert_action_template(result.context, result.value)
    return at, errors


# ---------------------------------------------------------------------------
# Milestone 5 checkpoint
# ---------------------------------------------------------------------------


def test_milestone5_checkpoint():
    f = File(
        name="action.yml",
        content="""
name: 'My Action'
description: 'A test action'
inputs:
  who-to-greet:
    description: 'Who to greet'
    required: true
    default: 'World'
runs:
  using: 'node20'
  main: 'index.js'
""",
    )
    result = parse_action(f, NoOperationTraceWriter())
    assert result.value is not None
    assert result.context.errors.count == 0


# ---------------------------------------------------------------------------
# Node actions
# ---------------------------------------------------------------------------


def test_node20_action():
    at, errors = _parse(
        """
name: JS Action
description: A JavaScript action
runs:
  using: node20
  main: dist/index.js
  pre: dist/setup.js
  pre-if: always()
  post: dist/cleanup.js
  post-if: always()
"""
    )
    assert len(errors) == 0
    assert at.name == "JS Action"
    assert isinstance(at.runs, ActionRunsNode)
    assert at.runs.using == "node20"
    assert at.runs.main == "dist/index.js"
    assert at.runs.pre == "dist/setup.js"
    assert at.runs.post == "dist/cleanup.js"
    assert at.runs.pre_if == "always()"
    assert at.runs.post_if == "always()"


def test_node_versions():
    for version in ("node12", "node16", "node20", "node24"):
        at, errors = _parse(
            f"""
name: Test
description: Test
runs:
  using: {version}
  main: index.js
"""
        )
        assert isinstance(at.runs, ActionRunsNode)
        assert at.runs.using == version


# ---------------------------------------------------------------------------
# Docker actions
# ---------------------------------------------------------------------------


def test_docker_action():
    at, errors = _parse(
        """
name: Docker Action
description: A Docker action
runs:
  using: docker
  image: Dockerfile
  entrypoint: /entrypoint.sh
  args:
    - ${{ inputs.name }}
  env:
    DEBUG: "true"
"""
    )
    assert len(errors) == 0
    assert isinstance(at.runs, ActionRunsDocker)
    assert at.runs.image == "Dockerfile"
    assert at.runs.entrypoint == "/entrypoint.sh"
    assert at.runs.args == ["${{ inputs.name }}"]
    assert at.runs.env == {"DEBUG": "true"}


# ---------------------------------------------------------------------------
# Composite actions
# ---------------------------------------------------------------------------


def test_composite_action():
    at, errors = _parse(
        """
name: Composite Action
description: Runs steps
runs:
  using: composite
  steps:
    - run: echo hello
      shell: bash
    - uses: actions/checkout@v4
"""
    )
    assert len(errors) == 0
    assert isinstance(at.runs, ActionRunsComposite)
    assert len(at.runs.steps) == 2


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def test_action_inputs():
    at, errors = _parse(
        """
name: Action with Inputs
description: Test inputs
inputs:
  name:
    description: The name
    required: true
    default: World
  verbose:
    description: Enable verbose
    required: false
  mode:
    description: Mode
    required: true
runs:
  using: composite
  steps: []
"""
    )
    assert len(errors) == 0
    assert at.inputs is not None
    assert len(at.inputs) == 3
    ids = [i.id for i in at.inputs]
    assert "name" in ids
    assert "verbose" in ids
    by_id = {i.id: i for i in at.inputs}
    assert by_id["name"].required is True
    assert by_id["name"].description == "The name"
    assert by_id["verbose"].required is False


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def test_action_outputs():
    at, errors = _parse(
        """
name: Action with Outputs
description: Test
outputs:
  greeting:
    description: The greeting
    value: ${{ steps.greet.outputs.message }}
runs:
  using: composite
  steps:
    - id: greet
      run: echo hello
      shell: bash
"""
    )
    assert len(errors) == 0
    assert at.outputs is not None
    assert len(at.outputs) == 1
    assert at.outputs[0].id == "greeting"
    assert at.outputs[0].description == "The greeting"


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------


def test_action_branding():
    at, errors = _parse(
        """
name: Branded Action
description: With branding
branding:
  icon: award
  color: blue
runs:
  using: composite
  steps: []
"""
    )
    assert len(errors) == 0
    assert at.branding is not None
    assert at.branding.icon == "award"
    assert at.branding.color == "blue"


# ---------------------------------------------------------------------------
# Author field
# ---------------------------------------------------------------------------


def test_action_author():
    at, errors = _parse(
        """
name: My Action
description: Test
author: GitHub
runs:
  using: composite
  steps: []
"""
    )
    assert len(errors) == 0
    assert at.author == "GitHub"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_invalid_yaml_reports_error():
    f = File(name="action.yml", content="name: test\ndescription: [\n")
    result = parse_action(f, NoOperationTraceWriter())
    assert result.context.errors.count >= 1
    assert result.value is None


def test_public_api_import():
    from py_actions_workflow_parser import parse_action, convert_action_template

    assert callable(parse_action)
    assert callable(convert_action_template)
