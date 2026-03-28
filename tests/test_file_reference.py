"""Tests for file_reference parsing utilities."""

from __future__ import annotations

import pytest

from py_actions_workflow_parser.workflows.file_reference import (
    LocalFileReference,
    RemoteFileReference,
    parse_file_reference,
    file_identifier,
)


# ---------------------------------------------------------------------------
# Local file references
# ---------------------------------------------------------------------------


def test_local_file_reference_dot_slash():
    ref = parse_file_reference("./.github/workflows/ci.yml")
    assert isinstance(ref, LocalFileReference)
    assert ref.path == ".github/workflows/ci.yml"


def test_local_file_reference_dot_dot():
    """../ paths are not supported as local refs; expect ValueError."""
    with pytest.raises(ValueError):
        parse_file_reference("../shared/workflow.yml")


def test_local_file_identifier():
    ref = LocalFileReference(path=".github/workflows/ci.yml")
    ident = file_identifier(ref)
    # file_identifier re-adds the ./ prefix stripped by parse_file_reference
    assert ident == "./.github/workflows/ci.yml"


# ---------------------------------------------------------------------------
# Remote file references
# ---------------------------------------------------------------------------


def test_remote_file_reference_basic():
    ref = parse_file_reference("owner/repo/.github/workflows/ci.yml@v1")
    assert isinstance(ref, RemoteFileReference)
    assert ref.owner == "owner"
    assert ref.repository == "repo"
    assert ref.path == ".github/workflows/ci.yml"
    assert ref.version == "v1"


def test_remote_file_reference_sha():
    ref = parse_file_reference("octocat/hello-world/.github/workflows/test.yml@abc1234")
    assert isinstance(ref, RemoteFileReference)
    assert ref.owner == "octocat"
    assert ref.repository == "hello-world"
    assert ref.version == "abc1234"


def test_remote_file_reference_branch():
    ref = parse_file_reference("org/repo/.github/workflows/deploy.yml@main")
    assert isinstance(ref, RemoteFileReference)
    assert ref.version == "main"


def test_remote_file_identifier():
    ref = RemoteFileReference(
        owner="owner",
        repository="repo",
        path=".github/workflows/ci.yml",
        version="v1",
    )
    ident = file_identifier(ref)
    assert "owner" in ident
    assert "repo" in ident
    assert "ci.yml" in ident


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_local_ref_with_only_dot_slash():
    ref = parse_file_reference("./action.yml")
    assert isinstance(ref, LocalFileReference)
    assert ref.path == "action.yml"
