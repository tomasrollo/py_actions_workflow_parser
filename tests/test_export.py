"""Tests for workflow_template_to_dict/json and action_template_to_dict/json."""

from __future__ import annotations

import json

import pytest

from py_actions_workflow_parser import (
    NoOperationTraceWriter,
    action_template_to_dict,
    action_template_to_json,
    convert_action_template,
    convert_workflow_template,
    parse_action,
    parse_workflow,
    workflow_template_to_dict,
    workflow_template_to_json,
)
from py_actions_workflow_parser.workflows.file import File


def _parse_workflow(content: str):
    f = File(name=".github/workflows/ci.yml", content=content)
    result = parse_workflow(f, NoOperationTraceWriter())
    return (
        convert_workflow_template(result.context, result.value),
        result.context.errors.get_errors(),
    )


def _parse_action(content: str):
    f = File(name="action.yml", content=content)
    result = parse_action(f, NoOperationTraceWriter())
    return (
        convert_action_template(result.context, result.value),
        result.context.errors.get_errors(),
    )


# ---------------------------------------------------------------------------
# workflow_template_to_dict
# ---------------------------------------------------------------------------


def test_simple_workflow_keys_present():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    assert "on" in d
    assert "jobs" in d
    assert d["on"] == {"push": {}}


def test_include_events_false():
    wt, _ = _parse_workflow(
        "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    d = workflow_template_to_dict(wt, include_events=False)
    assert "on" not in d
    assert "jobs" in d


def test_run_step_fields():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Say hello
        run: echo "hello"
        shell: bash
        working-directory: ./src
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    step = d["jobs"][0]["steps"][0]
    assert step["name"] == "Say hello"
    assert step["run"] == 'echo "hello"'
    assert step["shell"] == "bash"
    assert step["working-directory"] == "./src"


def test_action_step_fields():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 1
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    step = d["jobs"][0]["steps"][0]
    assert step["uses"] == "actions/checkout@v4"
    # with: values are always strings in GitHub Actions
    assert step["with"] == {"ref": "main", "fetch-depth": "1"}


def test_expression_in_runs_on():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - run: echo hi
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    job = d["jobs"][0]
    assert job["runs-on"] == "${{ matrix.os }}"


def test_env_mapping_plain():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      MY_VAR: hello
      ANOTHER: world
    steps: []
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    assert d["jobs"][0]["env"] == {"MY_VAR": "hello", "ANOTHER": "world"}


def test_workflow_level_env():
    wt, errors = _parse_workflow(
        """
on: push
env:
  GLOBAL: value
jobs:
  build:
    runs-on: ubuntu-latest
    steps: []
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    assert d["env"] == {"GLOBAL": "value"}


def test_workflow_dispatch_inputs():
    wt, errors = _parse_workflow(
        """
on:
  workflow_dispatch:
    inputs:
      env:
        description: Environment
        required: true
        type: choice
        options:
          - staging
          - production
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps: []
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    inputs = d["on"]["workflow_dispatch"]["inputs"]
    assert inputs["env"]["type"] == "choice"
    assert inputs["env"]["options"] == ["staging", "production"]
    assert inputs["env"]["required"] is True


def test_schedule_event():
    wt, errors = _parse_workflow(
        """
on:
  schedule:
    - cron: '0 0 * * *'
jobs:
  nightly:
    runs-on: ubuntu-latest
    steps: []
"""
    )
    assert not errors
    d = workflow_template_to_dict(wt)
    assert d["on"]["schedule"] == [{"cron": "0 0 * * *"}]


def test_needs_list():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps: []
  deploy:
    needs: [test]
    runs-on: ubuntu-latest
    steps: []
"""
    )
    assert not errors
    jobs = {j["id"]: j for j in workflow_template_to_dict(wt)["jobs"]}
    assert jobs["deploy"]["needs"] == ["test"]


def test_if_condition_on_step():
    wt, errors = _parse_workflow(
        """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo done
        if: success()
"""
    )
    assert not errors
    step = workflow_template_to_dict(wt)["jobs"][0]["steps"][0]
    assert step["if"] == "${{ success() }}"


def test_workflow_template_to_json_is_valid_json():
    wt, _ = _parse_workflow(
        "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps: []\n"
    )
    raw = workflow_template_to_json(wt)
    parsed = json.loads(raw)
    assert "jobs" in parsed


# ---------------------------------------------------------------------------
# action_template_to_dict
# ---------------------------------------------------------------------------


def test_node_action_export():
    at, errors = _parse_action(
        """
name: My Node Action
description: Does something
author: acme
runs:
  using: node20
  main: dist/index.js
  pre: dist/setup.js
  pre-if: always()
  post: dist/cleanup.js
  post-if: always()
"""
    )
    assert not errors
    d = action_template_to_dict(at)
    assert d["name"] == "My Node Action"
    assert d["description"] == "Does something"
    assert d["author"] == "acme"
    assert d["runs"]["using"] == "node20"
    assert d["runs"]["main"] == "dist/index.js"
    assert d["runs"]["pre"] == "dist/setup.js"
    assert d["runs"]["pre-if"] == "always()"
    assert d["runs"]["post"] == "dist/cleanup.js"
    assert d["runs"]["post-if"] == "always()"


def test_docker_action_export():
    at, errors = _parse_action(
        """
name: Docker Action
description: Runs in Docker
runs:
  using: docker
  image: Dockerfile
  entrypoint: /entrypoint.sh
  args:
    - --verbose
  env:
    MY_ENV: value
"""
    )
    assert not errors
    d = action_template_to_dict(at)
    assert d["runs"]["using"] == "docker"
    assert d["runs"]["image"] == "Dockerfile"
    assert d["runs"]["entrypoint"] == "/entrypoint.sh"
    assert d["runs"]["args"] == ["--verbose"]
    assert d["runs"]["env"] == {"MY_ENV": "value"}


def test_composite_action_steps_export():
    at, errors = _parse_action(
        """
name: Composite Action
description: Runs steps
runs:
  using: composite
  steps:
    - name: Checkout
      uses: actions/checkout@v4
    - name: Build
      run: make build
      shell: bash
"""
    )
    assert not errors
    d = action_template_to_dict(at)
    steps = d["runs"]["steps"]
    assert len(steps) == 2
    assert steps[0]["uses"] == "actions/checkout@v4"
    assert steps[1]["run"] == "make build"
    # shell is not extracted by the composite action step converter
    assert "shell" not in steps[1]


def test_action_inputs_and_outputs():
    at, errors = _parse_action(
        """
name: Greet
description: Says hello
inputs:
  who:
    description: Who to greet
    required: true
    default: World
outputs:
  greeting:
    description: The greeting
    value: ${{ steps.greet.outputs.message }}
runs:
  using: node20
  main: index.js
"""
    )
    assert not errors
    d = action_template_to_dict(at)
    inp = d["inputs"][0]
    assert inp["id"] == "who"
    assert inp["description"] == "Who to greet"
    assert inp["required"] is True
    assert inp["default"] == "World"

    out = d["outputs"][0]
    assert out["id"] == "greeting"
    assert out["value"] == "${{ steps.greet.outputs.message }}"


def test_action_branding():
    at, errors = _parse_action(
        """
name: Branded Action
description: Has branding
runs:
  using: node20
  main: index.js
branding:
  icon: activity
  color: blue
"""
    )
    assert not errors
    d = action_template_to_dict(at)
    assert d["branding"] == {"icon": "activity", "color": "blue"}


def test_action_template_to_json_is_valid_json():
    at, _ = _parse_action(
        """
name: Test
description: Test action
runs:
  using: node20
  main: index.js
"""
    )
    raw = action_template_to_json(at)
    parsed = json.loads(raw)
    assert parsed["name"] == "Test"
