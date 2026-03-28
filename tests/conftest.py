"""Shared pytest configuration and fixture test loader."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
import ruamel.yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).parent
_TESTDATA_DIR = _TESTS_DIR / "testdata" / "reader"
_SKIPPED_FILE = _TESTS_DIR / "testdata" / "skipped-tests.txt"

# ---------------------------------------------------------------------------
# WorkflowFixture — data carrier for one fixture test case
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class WorkflowFixture:
    name: str
    workflow_yaml: str
    expected_dict: dict[str, Any]
    include_events: bool


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_yaml = ruamel.yaml.YAML()


def _load_skipped() -> set[str]:
    if not _SKIPPED_FILE.exists():
        return set()
    return {
        line.strip() for line in _SKIPPED_FILE.read_text().splitlines() if line.strip()
    }


def load_workflow_fixtures() -> list[pytest.param]:
    """
    Load all workflow fixture .yml files from testdata/reader/ and return a
    list of pytest.param items — each annotated with the appropriate marks
    (xfail for skipped-tests.txt, skip for Python-incompatible cases).
    """
    if not _TESTDATA_DIR.exists():
        return []

    skipped = _load_skipped()
    cases: list[pytest.param] = []

    for path in sorted(_TESTDATA_DIR.glob("*.yml")):
        fname = path.name
        content = path.read_text(encoding="utf-8")
        parts = content.split("---\n")

        if len(parts) < 3:
            continue

        # Parse YAML header (doc[0])
        try:
            options = _yaml.load(parts[0]) or {}
        except Exception:
            options = {}

        skip_list: list[str] = options.get("skip", []) or []
        skip_set = {s.lower() for s in skip_list}

        # Parse expected JSON (last doc)
        try:
            expected_dict = json.loads(parts[-1])
        except Exception:
            continue

        # Determine marks
        marks: list[Any] = []

        if fname in skipped:
            marks.append(
                pytest.mark.xfail(reason="listed in skipped-tests.txt", strict=False)
            )
        elif "python" in skip_set:
            marks.append(
                pytest.mark.skip(reason="marked skip:Python in fixture header")
            )
        elif options.get("include-source", False):
            marks.append(
                pytest.mark.skip(
                    reason="include-source:true requires source metadata serialization"
                )
            )
        elif "reusable" in fname and len(parts) > 3:
            marks.append(
                pytest.mark.skip(
                    reason="reusable workflow multi-doc fixture not yet supported"
                )
            )
        elif "file-table" in expected_dict or "input-types" in expected_dict:
            marks.append(
                pytest.mark.skip(
                    reason="file-table/input-types output format not supported"
                )
            )

        include_events = "go" in skip_set and "c#" in skip_set

        fixture = WorkflowFixture(
            name=fname,
            workflow_yaml=parts[1],
            expected_dict=expected_dict,
            include_events=include_events,
        )
        cases.append(pytest.param(fixture, id=fname, marks=marks))

    return cases
