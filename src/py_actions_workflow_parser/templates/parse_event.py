"""Parse events and their types for the template reader."""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tokens.template_token import TemplateToken


class EventType(IntEnum):
    Literal = 0
    SequenceStart = 1
    SequenceEnd = 2
    MappingStart = 3
    MappingEnd = 4
    DocumentStart = 5
    DocumentEnd = 6


class ParseEvent:
    __slots__ = ("type", "token")

    def __init__(self, type: EventType, token: "TemplateToken | None" = None) -> None:
        self.type = type
        self.token = token
