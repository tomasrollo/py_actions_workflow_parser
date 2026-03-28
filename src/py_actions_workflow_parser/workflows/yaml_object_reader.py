"""YamlObjectReader — reads a YAML document and exposes it as parse events."""

from __future__ import annotations

import io
from typing import Generator, Iterator

from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError
from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode

from ..templates.object_reader import ObjectReader
from ..templates.parse_event import EventType, ParseEvent
from ..tokens.boolean_token import BooleanToken
from ..tokens.literal_token import LiteralToken
from ..tokens.mapping_token import MappingToken
from ..tokens.null_token import NullToken
from ..tokens.number_token import NumberToken
from ..tokens.sequence_token import SequenceToken
from ..tokens.string_token import StringToken
from ..tokens.token_range import Position, TokenRange

# ---- YAML tags ---------------------------------------------------------------

_TAG_NULL = "tag:yaml.org,2002:null"
_TAG_BOOL = "tag:yaml.org,2002:bool"
_TAG_INT = "tag:yaml.org,2002:int"
_TAG_FLOAT = "tag:yaml.org,2002:float"
_TAG_STR = "tag:yaml.org,2002:str"
_TAG_SEQ = "tag:yaml.org,2002:seq"
_TAG_MAP = "tag:yaml.org,2002:map"

# ---- helpers -----------------------------------------------------------------


def _mark_to_position(mark: object) -> Position:
    """Convert a ruamel.yaml Mark (0-based) to a 1-based Position."""
    # mark has .line and .column (both 0-based)
    return Position(getattr(mark, "line", 0) + 1, getattr(mark, "column", 0) + 1)


def _node_range(node: object) -> TokenRange | None:
    start_mark = getattr(node, "start_mark", None)
    end_mark = getattr(node, "end_mark", None)
    if start_mark is None:
        return None
    end = (
        _mark_to_position(end_mark)
        if end_mark is not None
        else _mark_to_position(start_mark)
    )
    return TokenRange(_mark_to_position(start_mark), end)


def _parse_bool(raw: str) -> bool:
    return raw.lower() in ("true", "yes", "on", "1")


def _parse_number(raw: str) -> int | float:
    # Handle YAML int/float representations
    stripped = raw.strip()
    # hex
    if stripped.startswith(("0x", "0X", "-0x", "-0X")):
        return int(stripped, 16)
    # octal
    if stripped.startswith(("0o", "0O", "-0o", "-0O")):
        return int(stripped, 8)
    # binary
    if stripped.startswith(("0b", "0B", "-0b", "-0B")):
        return int(stripped, 2)
    try:
        return int(stripped, 10)
    except ValueError:
        return float(stripped)


def _build_literal_token(
    file_id: int | None,
    node: ScalarNode,
) -> LiteralToken:
    tag = node.tag or ""
    raw = node.value  # always a str at the node level
    rng = _node_range(node)

    if tag == _TAG_NULL or (tag == "" and raw in ("", "~", "null", "Null", "NULL")):
        return NullToken(file_id, rng, None)

    if tag == _TAG_BOOL:
        return BooleanToken(file_id, rng, _parse_bool(raw), None)

    if tag in (_TAG_INT, _TAG_FLOAT):
        # YAML 1.2 core schema does not allow underscores in numbers (that's a
        # YAML 1.1 extension). If the raw value contains underscores, treat it
        # as a plain string to match strict YAML 1.2 behavior.
        if "_" not in raw:
            return NumberToken(file_id, rng, _parse_number(raw), None)
        # Fall through to string handling for e.g. "12_345" or "23_456.789"

    # Everything else is a string (including explicit !!str)
    style = getattr(node, "style", None)  # '|', '>', "'", '"', or None for plain
    block_scalar_header: str | None = None
    if style == "|":
        block_scalar_header = "|"
    elif style == ">":
        block_scalar_header = ">"
        # ruamel.yaml uses \x07 as an internal placeholder in the node value for
        # folded block scalars — strip them to get the resolved string value.
        raw = raw.replace("\x07", "")

    # The "source" field is the raw original YAML scalar text. For scalars
    # loaded via the node tree, we expose the raw value string.
    source: str | None = raw if style else None

    return StringToken(file_id, rng, raw, None, source, block_scalar_header)


# ---- Generator ---------------------------------------------------------------


def _get_nodes(
    node: object,
    file_id: int | None,
    visited: set[int],
) -> Generator[ParseEvent, None, None]:
    """Recursively yield ParseEvents from a ruamel.yaml node tree."""

    if node is None:
        yield ParseEvent(EventType.Literal, NullToken(file_id, None, None))
        return

    if isinstance(node, SequenceNode):
        yield ParseEvent(
            EventType.SequenceStart, SequenceToken(file_id, _node_range(node), None)
        )
        for child in node.value:
            yield from _get_nodes(child, file_id, visited)
        yield ParseEvent(EventType.SequenceEnd)

    elif isinstance(node, MappingNode):
        yield ParseEvent(
            EventType.MappingStart, MappingToken(file_id, _node_range(node), None)
        )
        for key_node, value_node in node.value:
            # Key must be a scalar (string) in GitHub Actions YAML
            key_range = _node_range(key_node)
            key_str = (
                str(key_node.value)
                if isinstance(key_node, ScalarNode)
                else str(key_node)
            )
            yield ParseEvent(
                EventType.Literal, StringToken(file_id, key_range, key_str, None)
            )
            # ruamel.yaml places implicit null values (from `key:\n`) at the
            # start of the next token rather than right after the ':'.  Match
            # the TS yaml-library behaviour by positioning the null right after
            # the colon: key_start_column + len(key) + 1  (0-indexed).
            if (
                isinstance(value_node, ScalarNode)
                and value_node.tag == _TAG_NULL
                and isinstance(key_node, ScalarNode)
                and key_node.start_mark is not None
                and value_node.start_mark is not None
                and value_node.start_mark.line != key_node.start_mark.line
            ):
                adj_col_0 = key_node.start_mark.column + len(key_str) + 1
                adj_line = key_node.start_mark.line + 1  # 1-indexed
                adj_col = adj_col_0 + 1  # 1-indexed
                rng = TokenRange(
                    Position(adj_line, adj_col), Position(adj_line, adj_col)
                )
                yield ParseEvent(EventType.Literal, NullToken(file_id, rng, None))
            else:
                yield from _get_nodes(value_node, file_id, visited)
        yield ParseEvent(EventType.MappingEnd)

    elif isinstance(node, ScalarNode):
        yield ParseEvent(EventType.Literal, _build_literal_token(file_id, node))

    else:
        # Handle alias nodes (same Python object appearing twice) using identity tracking
        node_id = id(node)
        if node_id in visited:
            return  # circular alias — skip silently
        visited_copy = set(visited)
        visited_copy.add(node_id)
        yield from _get_nodes(node, file_id, visited_copy)


# ---- Public class ------------------------------------------------------------


class YamlError:
    __slots__ = ("message", "range")

    def __init__(self, message: str, range: TokenRange | None) -> None:
        self.message = message
        self.range = range


class YamlObjectReader(ObjectReader):
    """Reads a YAML document and exposes it via the ObjectReader interface."""

    def __init__(self, file_id: int | None, content: str) -> None:
        self._file_id = file_id
        self.errors: list[YamlError] = []
        self._events: list[ParseEvent] = []
        self._pos: int = 0

        yaml = YAML()
        yaml.preserve_quotes = True  # type: ignore[assignment]

        try:
            node = yaml.compose(io.StringIO(content))
        except MarkedYAMLError as exc:
            # Collect the parse error and use an empty document
            range_: TokenRange | None = None
            if exc.problem_mark is not None:
                p = _mark_to_position(exc.problem_mark)
                range_ = TokenRange(p, p)
            self.errors.append(YamlError(str(exc.problem or exc), range_))
            node = None

        # Build the full event list upfront (mirrors the TS generator approach)
        self._events.append(ParseEvent(EventType.DocumentStart))
        if node is not None:
            for event in _get_nodes(node, file_id, set()):
                self._events.append(event)
        self._events.append(ParseEvent(EventType.DocumentEnd))

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
