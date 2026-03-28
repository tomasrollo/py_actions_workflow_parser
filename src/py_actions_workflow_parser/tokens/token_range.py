"""Position and TokenRange types for source location tracking."""

from dataclasses import dataclass


@dataclass
class Position:
    """A one-based line/column position within a template source file."""

    line: int
    column: int


@dataclass
class TokenRange:
    """Start and end positions of a token within a source file."""

    start: Position
    end: Position
