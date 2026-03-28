"""Template reader — validates and builds a TemplateToken DOM from an ObjectReader."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..schema.definition_info import DefinitionInfo
from ..schema.definition_type import DefinitionType
from ..schema.mapping_definition import MappingDefinition
from ..schema.sequence_definition import SequenceDefinition
from ..templates.template_constants import (
    ANY,
    CLOSE_EXPRESSION,
    INSERT_DIRECTIVE,
    OPEN_EXPRESSION,
)
from ..tokens.basic_expression_token import BasicExpressionToken
from ..tokens.expression_token import ExpressionToken
from ..tokens.insert_expression_token import InsertExpressionToken
from ..tokens.literal_token import LiteralToken
from ..tokens.mapping_token import MappingToken
from ..tokens.scalar_token import ScalarToken
from ..tokens.string_token import StringToken
from ..tokens.template_token import TemplateToken
from ..tokens.token_range import Position, TokenRange
from ..tokens.type_guards import is_string
from ..tokens.types import TokenType

if TYPE_CHECKING:
    from ..templates.object_reader import ObjectReader
    from ..templates.template_context import TemplateContext

_WHITESPACE_PATTERN = re.compile(r"\s")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def read_template(
    context: "TemplateContext",
    type: str,
    object_reader: "ObjectReader",
    file_id: int | None,
) -> TemplateToken | None:
    reader = _TemplateReader(context, object_reader, file_id)
    value: TemplateToken | None = None
    try:
        object_reader.validate_start()
        definition = DefinitionInfo(context.schema, type)
        value = reader.read_value(definition)
        object_reader.validate_end()
    except Exception as err:
        context.error(file_id, err)
    return value


# ---------------------------------------------------------------------------
# Internal reader class
# ---------------------------------------------------------------------------


class _TemplateReader:
    def __init__(
        self,
        context: "TemplateContext",
        object_reader: "ObjectReader",
        file_id: int | None,
    ) -> None:
        self._context = context
        self._schema = context.schema
        self._object_reader = object_reader
        self._file_id = file_id

    # ---- read_value ----------------------------------------------------------

    def read_value(self, definition: DefinitionInfo) -> TemplateToken:
        # Scalar
        literal = self._object_reader.allow_literal()
        if literal is not None:
            scalar = self._parse_scalar(literal, definition)
            scalar = self._validate(scalar, definition)
            return scalar

        # Sequence
        sequence = self._object_reader.allow_sequence_start()
        if sequence is not None:
            seq_defs = definition.get_definitions_of_type(DefinitionType.Sequence)
            sequence_definition: SequenceDefinition | None = seq_defs[0] if seq_defs else None  # type: ignore[assignment]

            if sequence_definition is not None:
                item_definition = DefinitionInfo(
                    definition, sequence_definition.item_type
                )
                while not self._object_reader.allow_sequence_end():
                    item = self.read_value(item_definition)
                    sequence.add(item)
            else:
                self._context.error(sequence, "A sequence was not expected")
                while not self._object_reader.allow_sequence_end():
                    self._skip_value()

            sequence.definition_info = definition
            return sequence

        # Mapping
        mapping = self._object_reader.allow_mapping_start()
        if mapping is not None:
            mapping_definitions: list[MappingDefinition] = definition.get_definitions_of_type(DefinitionType.Mapping)  # type: ignore[assignment]

            if mapping_definitions:
                first = mapping_definitions[0]
                if (
                    len(mapping_definitions) > 1
                    or first.properties
                    or not first.loose_key_type
                ):
                    self._handle_mapping_with_well_known_properties(
                        definition, mapping_definitions, mapping
                    )
                else:
                    key_def = DefinitionInfo(definition, first.loose_key_type)
                    val_def = DefinitionInfo(definition, first.loose_value_type)  # type: ignore[arg-type]
                    self._handle_mapping_with_all_loose_properties(
                        definition, key_def, val_def, first, mapping
                    )
            else:
                self._context.error(mapping, "A mapping was not expected")
                while not self._object_reader.allow_mapping_end():
                    self._skip_value()
                    self._skip_value()

            if not mapping.definition_info:
                mapping.definition_info = definition

            return mapping

        raise RuntimeError("Expected a scalar value, a sequence, or a mapping")

    # ---- _handle_mapping_with_well_known_properties --------------------------

    def _handle_mapping_with_well_known_properties(
        self,
        definition: DefinitionInfo,
        mapping_definitions: list[MappingDefinition],
        mapping: MappingToken,
    ) -> None:
        loose_key_type: str | None = None
        loose_value_type: str | None = None
        loose_key_definition: DefinitionInfo | None = None
        loose_value_definition: DefinitionInfo | None = None

        if mapping_definitions[0].loose_key_type:
            loose_key_type = mapping_definitions[0].loose_key_type
            loose_value_type = mapping_definitions[0].loose_value_type

        upper_keys: dict[str, bool] = {}
        has_expression_key = False

        raw_literal = self._object_reader.allow_literal()
        while raw_literal is not None:
            next_key_scalar = self._parse_scalar(raw_literal, definition)

            # Expression key
            if next_key_scalar.is_expression:
                has_expression_key = True
                if definition.allowed_context:
                    any_definition = DefinitionInfo(definition, ANY)
                    mapping.add(next_key_scalar, self.read_value(any_definition))
                else:
                    self._context.error(
                        next_key_scalar,
                        "A template expression is not allowed in this context",
                    )
                    self._skip_value()
                raw_literal = self._object_reader.allow_literal()
                continue

            # Convert to StringToken if needed
            if next_key_scalar.template_token_type == TokenType.String:
                next_key = next_key_scalar  # type: ignore[assignment]
            else:
                next_key = StringToken(
                    next_key_scalar.file,
                    next_key_scalar.range,
                    str(next_key_scalar),
                    next_key_scalar.definition_info,
                )

            # Duplicate check
            if next_key.value:
                upper_key = next_key.value.upper()
                if upper_keys.get(upper_key):
                    self._context.error(
                        next_key, f"'{next_key.value}' is already defined"
                    )
                    self._skip_value()
                    raw_literal = self._object_reader.allow_literal()
                    continue
                upper_keys[upper_key] = True

            # Well-known property
            next_property_def = self._schema.match_property_and_filter(
                mapping_definitions, next_key.value
            )
            if next_property_def is not None:
                next_definition = DefinitionInfo(definition, next_property_def.type)
                next_key.definition_info = next_definition
                if next_property_def.description:
                    next_key.description = next_property_def.description  # type: ignore[attr-defined]
                next_value = self.read_value(next_definition)
                mapping.add(next_key, next_value)
                raw_literal = self._object_reader.allow_literal()
                continue

            # Loose property
            if loose_key_type:
                if loose_key_definition is None:
                    loose_key_definition = DefinitionInfo(definition, loose_key_type)
                    loose_value_definition = DefinitionInfo(definition, loose_value_type)  # type: ignore[arg-type]

                self._validate(next_key, loose_key_definition)

                next_definition = DefinitionInfo(definition, mapping_definitions[0].loose_value_type)  # type: ignore[arg-type]
                next_key.definition_info = next_definition
                next_value = self.read_value(loose_value_definition)  # type: ignore[arg-type]
                mapping.add(next_key, next_value)
                raw_literal = self._object_reader.allow_literal()
                continue

            # Unknown property
            self._context.error(next_key, f"Unexpected value '{next_key.value}'")
            self._skip_value()
            raw_literal = self._object_reader.allow_literal()

        # Narrow to single definition if possible
        if len(mapping_definitions) == 1:
            mapping.definition_info = DefinitionInfo(definition, mapping_definitions[0])
        elif len(mapping_definitions) > 1:
            hit_count: dict[str, int] = {}
            for md in mapping_definitions:
                for key in md.properties:
                    hit_count[key] = hit_count.get(key, 0) + 1
            non_duplicates = sorted(k for k, v in hit_count.items() if v == 1)
            self._context.error(
                mapping,
                f"There's not enough info to determine what you meant. Add one of these properties: {', '.join(non_duplicates)}",
            )

        # Check required properties
        if len(mapping_definitions) == 1 and not has_expression_key:
            for prop_name, prop_def in mapping_definitions[0].properties.items():
                if prop_def.required and not upper_keys.get(prop_name.upper()):
                    self._context.error(
                        mapping, f"Required property is missing: {prop_name}"
                    )

        self._expect_mapping_end()

    # ---- _handle_mapping_with_all_loose_properties ---------------------------

    def _handle_mapping_with_all_loose_properties(
        self,
        definition: DefinitionInfo,
        key_definition: DefinitionInfo,
        value_definition: DefinitionInfo,
        mapping_definition: MappingDefinition,
        mapping: MappingToken,
    ) -> None:
        upper_keys: dict[str, bool] = {}

        raw_literal = self._object_reader.allow_literal()
        while raw_literal is not None:
            next_key_scalar = self._parse_scalar(raw_literal, definition)
            next_key_scalar.definition_info = key_definition

            # Expression key
            if next_key_scalar.is_expression:
                if definition.allowed_context:
                    next_value = self.read_value(value_definition)
                    mapping.add(next_key_scalar, next_value)
                else:
                    self._context.error(
                        next_key_scalar,
                        "A template expression is not allowed in this context",
                    )
                    self._skip_value()
                raw_literal = self._object_reader.allow_literal()
                continue

            # Convert to StringToken if needed
            if next_key_scalar.template_token_type == TokenType.String:
                next_key = next_key_scalar  # type: ignore[assignment]
            else:
                next_key = StringToken(
                    next_key_scalar.file,
                    next_key_scalar.range,
                    str(next_key_scalar),
                    next_key_scalar.definition_info,
                )

            # Duplicate
            if next_key.value:
                upper_key = next_key.value.upper()
                if upper_keys.get(upper_key):
                    self._context.error(
                        next_key, f"'{next_key.value}' is already defined"
                    )
                    self._skip_value()
                    raw_literal = self._object_reader.allow_literal()
                    continue
                upper_keys[upper_key] = True

            self._validate(next_key, key_definition)

            next_definition = DefinitionInfo(definition, mapping_definition.loose_value_type)  # type: ignore[arg-type]
            next_key.definition_info = next_definition
            next_value = self.read_value(value_definition)
            mapping.add(next_key, next_value)
            raw_literal = self._object_reader.allow_literal()

        self._expect_mapping_end()

    # ---- helpers -------------------------------------------------------------

    def _expect_mapping_end(self) -> None:
        if not self._object_reader.allow_mapping_end():
            raise RuntimeError("Expected mapping end")

    def _skip_value(self) -> None:
        if self._object_reader.allow_literal():
            return
        if self._object_reader.allow_sequence_start():
            while not self._object_reader.allow_sequence_end():
                self._skip_value()
            return
        if self._object_reader.allow_mapping_start():
            while not self._object_reader.allow_mapping_end():
                self._skip_value()
                self._skip_value()
            return
        raise RuntimeError("Expected a scalar value, a sequence, or a mapping")

    def _validate(self, scalar: ScalarToken, definition: DefinitionInfo) -> ScalarToken:
        tt = scalar.template_token_type
        if tt in (
            TokenType.Null,
            TokenType.Boolean,
            TokenType.Number,
            TokenType.String,
        ):
            literal = scalar  # type: ignore[assignment]
            scalar_defs = definition.get_scalar_definitions()
            for sd in scalar_defs:
                if sd.is_match(literal):
                    scalar.definition_info = DefinitionInfo(definition, sd)
                    return scalar

            # Try coercing to string
            if literal.template_token_type != TokenType.String:
                string_literal = StringToken(
                    literal.file,
                    literal.range,
                    str(literal),
                    literal.definition_info,
                )
                for sd in scalar_defs:
                    if sd.is_match(string_literal):
                        string_literal.definition_info = DefinitionInfo(definition, sd)
                        return string_literal

            self._context.error(literal, f"Unexpected value '{literal!s}'")
            return scalar

        if tt == TokenType.BasicExpression:
            if not definition.allowed_context:
                self._context.error(
                    scalar, "A template expression is not allowed in this context"
                )
            return scalar

        self._context.error(scalar, f"Unexpected value '{scalar!s}'")
        return scalar

    # ---- _parse_scalar -------------------------------------------------------

    def _parse_scalar(
        self, token: LiteralToken, definition_info: DefinitionInfo
    ) -> ScalarToken:
        if not is_string(token) or not token.value:
            return token

        allowed_context = definition_info.allowed_context
        is_single_line = (
            token.range is None or token.range.start.line == token.range.end.line
        )

        raw = token.value if is_single_line else (token.source or token.value)

        start_expression = raw.find(OPEN_EXPRESSION)
        if start_expression < 0:
            return token

        encountered_error = False
        segments: list[ScalarToken] = []
        i = 0

        while i < len(raw):
            if i == start_expression:
                # Find matching "}}"
                end_expression = -1
                in_string = False
                j = i + len(OPEN_EXPRESSION)
                while j < len(raw):
                    if raw[j] == "'":
                        in_string = not in_string
                    elif not in_string and raw[j] == "}" and raw[j - 1] == "}":
                        end_expression = j
                        j += 1
                        break
                    j += 1
                i = j

                if end_expression < start_expression:
                    self._context.error(
                        token,
                        "The expression is not closed. An unescaped ${{ sequence was found, but the closing }} sequence was not found.",
                    )
                    return token

                raw_expression = raw[
                    start_expression
                    + len(OPEN_EXPRESSION) : end_expression
                    - len(CLOSE_EXPRESSION)
                    + 1
                ]

                # Build token range for the expression
                tr = token.range or TokenRange(Position(1, 1), Position(1, 1))
                if is_single_line:
                    offset = (token.source or raw).find(OPEN_EXPRESSION) - raw.find(
                        OPEN_EXPRESSION
                    )
                    tr = TokenRange(
                        Position(
                            tr.start.line, tr.start.column + start_expression + offset
                        ),
                        Position(
                            tr.end.line, tr.start.column + end_expression + 1 + offset
                        ),
                    )
                else:
                    start_raw = raw[:start_expression]
                    adjusted_start_line = start_raw.count("\n") + 1
                    beginning_of_line = start_raw.rfind("\n")
                    adjusted_start = start_expression - beginning_of_line
                    adjusted_end = end_expression - beginning_of_line + 1
                    tr = TokenRange(
                        Position(tr.start.line + adjusted_start_line, adjusted_start),
                        Position(tr.start.line + adjusted_start_line, adjusted_end),
                    )

                expression = self._parse_into_expression_token(
                    tr, raw_expression, allowed_context, token, definition_info
                )

                if expression is None:
                    encountered_error = True
                else:
                    if expression.directive and (start_expression != 0 or i < len(raw)):
                        self._context.error(
                            token,
                            f"The directive '{expression.directive}' is not allowed in this context. "
                            "Directives are not supported for expressions that are embedded within a string. "
                            "Directives are only supported when the entire value is an expression.",
                        )
                        return token
                    segments.append(expression)

                start_expression = raw.find(OPEN_EXPRESSION, i)

            elif i < start_expression:
                self._add_string(
                    segments,
                    token.range,
                    raw[i:start_expression],
                    token.definition_info,
                )
                i = start_expression
            else:
                self._add_string(segments, token.range, raw[i:], token.definition_info)
                break

        if encountered_error:
            return token

        # Single basic expression: check for escaped literal
        if (
            len(segments) == 1
            and segments[0].template_token_type == TokenType.BasicExpression
        ):
            basic_expression = segments[0]  # type: ignore[assignment]
            str_val = self._get_expression_string(basic_expression.expression)
            if str_val is not None:
                return StringToken(
                    self._file_id, token.range, str_val, token.definition_info
                )

        if len(segments) == 1:
            return segments[0]

        # Multiple segments: combine with format()
        fmt_parts: list[str] = []
        args: list[str] = []
        expression_tokens: list[BasicExpressionToken] = []
        arg_index = 0

        for segment in segments:
            if is_string(segment):
                text = (
                    segment.value.replace("'", "''")
                    .replace("{", "{{")
                    .replace("}", "}}")
                )
                fmt_parts.append(text)
            else:
                fmt_parts.append(f"{{{arg_index}}}")
                arg_index += 1
                expr = segment  # type: ignore[assignment]
                args.append(", ")
                args.append(expr.expression)
                expression_tokens.append(expr)

        return BasicExpressionToken(
            self._file_id,
            token.range,
            f"format('{(''.join(fmt_parts))}'{(''.join(args))})",
            definition_info,
            expression_tokens,
            raw,
            None,
            getattr(token, "block_scalar_header", None),
        )

    # ---- _parse_into_expression_token ----------------------------------------

    def _parse_into_expression_token(
        self,
        tr: TokenRange,
        raw_expression: str,
        allowed_context: list[str],
        token: StringToken,
        definition_info: DefinitionInfo | None,
    ) -> ExpressionToken | None:
        result = self._parse_expression(
            tr, token, raw_expression, allowed_context, definition_info
        )
        if result.error is not None:
            self._context.error(token, result.error, tr)
            return None
        return result.expression

    # ---- _parse_expression ---------------------------------------------------

    def _parse_expression(
        self,
        range: TokenRange,
        token: StringToken,
        value: str,
        allowed_context: list[str],
        definition_info: DefinitionInfo | None,
    ) -> "_ParseExpressionResult":
        trimmed = value.strip()

        if not trimmed:
            return _ParseExpressionResult(
                None, RuntimeError("An expression was expected")
            )

        # Check for insert directive
        match_result = self._match_directive(trimmed, INSERT_DIRECTIVE, 0)
        if match_result.is_match:
            return _ParseExpressionResult(
                InsertExpressionToken(self._file_id, range, definition_info), None
            )
        if match_result.error is not None:
            return _ParseExpressionResult(None, match_result.error)

        # Validate expression
        try:
            ExpressionToken.validate_expression(trimmed, allowed_context)
        except Exception as err:
            return _ParseExpressionResult(None, err)

        start_trim = len(value) - len(value.lstrip())
        end_trim = len(value) - len(value.rstrip())

        expression_range = TokenRange(
            Position(
                range.start.line, range.start.column + len(OPEN_EXPRESSION) + start_trim
            ),
            Position(
                range.end.line, range.end.column - len(CLOSE_EXPRESSION) - end_trim
            ),
        )

        return _ParseExpressionResult(
            BasicExpressionToken(
                self._file_id,
                range,
                trimmed,
                definition_info,
                None,
                token.source,
                expression_range,
                getattr(token, "block_scalar_header", None),
            ),
            None,
        )

    # ---- _add_string ---------------------------------------------------------

    def _add_string(
        self,
        segments: list[ScalarToken],
        range: TokenRange | None,
        value: str,
        definition: DefinitionInfo | None,
    ) -> None:
        if segments and segments[-1].template_token_type == TokenType.String:
            last = segments[-1]  # type: ignore[assignment]
            segments[-1] = StringToken(
                self._file_id, range, last.value + value, definition
            )
        else:
            segments.append(StringToken(self._file_id, range, value, definition))

    # ---- _match_directive ----------------------------------------------------

    def _match_directive(
        self,
        trimmed: str,
        directive: str,
        expected_parameters: int,
    ) -> "_MatchDirectiveResult":
        parameters: list[str] = []
        if trimmed.startswith(directive) and (
            len(trimmed) == len(directive)
            or _WHITESPACE_PATTERN.match(trimmed[len(directive)])
        ):
            start_index = len(directive)
            in_string = False
            parens = 0

            for i in range(start_index, len(trimmed)):
                c = trimmed[i]
                if _WHITESPACE_PATTERN.match(c) and not in_string and parens == 0:
                    if start_index < i:
                        parameters.append(trimmed[start_index:i])
                    start_index = i + 1
                elif c == "'":
                    in_string = not in_string
                elif c == "(" and not in_string:
                    parens += 1
                elif c == ")" and not in_string:
                    parens -= 1

            if start_index < len(trimmed):
                parameters.append(trimmed[start_index:])

            if expected_parameters != len(parameters):
                return _MatchDirectiveResult(
                    False,
                    parameters,
                    RuntimeError(
                        f"Exactly {expected_parameters} parameter(s) were expected following the "
                        f"directive '{directive}'. Actual parameter count: {len(parameters)}"
                    ),
                )

            return _MatchDirectiveResult(True, parameters, None)

        return _MatchDirectiveResult(False, parameters, None)

    # ---- _get_expression_string ----------------------------------------------

    def _get_expression_string(self, trimmed: str) -> str | None:
        result: list[str] = []
        in_string = False

        for i, c in enumerate(trimmed):
            if c == "'":
                in_string = not in_string
                if in_string and i != 0:
                    result.append(c)
            elif not in_string:
                return None
            else:
                result.append(c)

        return "".join(result)


# ---------------------------------------------------------------------------
# Helper dataclasses
# ---------------------------------------------------------------------------


@dataclass
class _ParseExpressionResult:
    expression: ExpressionToken | None
    error: Exception | None


@dataclass
class _MatchDirectiveResult:
    is_match: bool
    parameters: list[str]
    error: Exception | None
