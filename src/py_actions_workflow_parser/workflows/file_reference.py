"""File reference types and parsing for workflow file references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass
class LocalFileReference:
    path: str


@dataclass
class RemoteFileReference:
    owner: str
    repository: str
    path: str
    version: str


FileReference = Union[LocalFileReference, RemoteFileReference]


def parse_file_reference(ref: str) -> FileReference:
    """Parse a workflow file reference into a LocalFileReference or RemoteFileReference."""
    if ref.startswith("./"):
        return LocalFileReference(path=ref[2:])

    parts = ref.split("@", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid file reference: {ref}")

    remote_path, version = parts
    segments = [s for s in remote_path.split("/") if s]

    if len(segments) < 2 or not version:
        raise ValueError(f"Invalid file reference: {ref}")

    owner = segments[0]
    repository = segments[1]
    path = "/".join(segments[2:])

    return RemoteFileReference(
        owner=owner, repository=repository, path=path, version=version
    )


def file_identifier(ref: FileReference) -> str:
    """Return a canonical string identifier for a file reference."""
    if isinstance(ref, LocalFileReference):
        return "./" + ref.path
    return f"{ref.owner}/{ref.repository}/{ref.path}@{ref.version}"
