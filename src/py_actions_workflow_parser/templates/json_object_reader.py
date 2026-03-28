"""JSONObjectReader — reads a JSON document and exposes it as parse events."""

from __future__ import annotations

import json
from typing import Any, Generator

from ..templates.object_reader import ObjectReader
from ..templates.parse_event import EventType, ParseEvent
from ..tokens.boolean_token import BooleanToken
from ..tokens.literal_token import LiteralToken
from ..tokens.mapping_token import MappingToken
from ..tokens.null_token import NullToken
from ..tokens.number_token import NumberToken
from ..tokens.sequence_token import SequenceToken
from ..tokens.string_token import StringToken


def _get_parse_events(
    file_id: int | None,
    value: Any,
    root: bool = False,
) -> Generator[ParseEvent, None, None]:
    """Depth-first generator of ParseEvents from a Python value."""
    if root:
        yield ParseEvent(EventType.DocumentStart)

    if value is None:
        yield ParseEvent(EventType.Literal, NullToken(file_id, None, None))
    elif isinstance(value, bool):
        yield ParseEvent(EventType.Literal, BooleanToken(file_id, None, value, None))
    elif isinstance(value, (int, float)):
        yield ParseEvent(EventType.Literal, NumberToken(file_id, None, value, None))
    elif isinstance(value, str):
        yield ParseEvent(EventType.Literal, StringToken(file_id, None, value, None))
    elif isinstance(value, list):
        yield ParseEvent(EventType.SequenceStart, SequenceToken(file_id, None, None))
        for item in value:
            yield from _get_parse_events(file_id, item)
        yield ParseEvent(EventType.SequenceEnd)
    elif isinstance(value, dict):
        yield ParseEvent(EventType.MappingStart, MappingToken(file_id, None, None))
        for key, val in value.items():
            yield ParseEvent(
                EventType.Literal, StringToken(file_id, None, str(key), None)
            )
            yield from _get_parse_events(file_id, val)
        yield ParseEvent(EventType.MappingEnd)
    else:
        raise TypeError(
            f"Unexpected value type '{type(value).__name__}' when reading object"
        )

    if root:
        yield ParseEvent(EventType.DocumentEnd)


class JSONObjectReader(ObjectReader):
    """Reads a JSON string and exposes it via the ObjectReader interface."""

    def __init__(self, file_id: int | None, input: str) -> None:
        self._file_id = file_id
        value = json.loads(input)
        self._events: list[ParseEvent] = list(
            _get_parse_events(file_id, value, root=True)
        )
        self._pos: int = 0

    # ---- ObjectReader interface -----------------------------------------------

    def allow_literal(self) -> LiteralToken | None:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.Literal:
                self._pos += 1
                return event.token  # type: ignore[return-value]
        return None

    def allow_sequence_start(self) -> SequenceToken | None:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.SequenceStart:
                self._pos += 1
                return event.token  # type: ignore[return-value]
        return None

    def allow_sequence_end(self) -> bool:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.SequenceEnd:
                self._pos += 1
                return True
        return False

    def allow_mapping_start(self) -> MappingToken | None:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.MappingStart:
                self._pos += 1
                return event.token  # type: ignore[return-value]
        return None

    def allow_mapping_end(self) -> bool:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.MappingEnd:
                self._pos += 1
                return True
        return False

    def validate_start(self) -> None:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.DocumentStart:
                self._pos += 1
                return
        raise RuntimeError("Expected start of reader")

    def validate_end(self) -> None:
        if self._pos < len(self._events):
            event = self._events[self._pos]
            if event.type == EventType.DocumentEnd:
                self._pos += 1
                return
        raise RuntimeError("Expected end of reader")
