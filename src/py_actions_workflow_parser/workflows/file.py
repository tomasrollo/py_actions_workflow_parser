"""File — represents a source file to be parsed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class File:
    name: str
    content: str
