"""TemplateToken abstract base class and TemplateTokenError."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generator

from .token_range import TokenRange
from .types import TokenType, token_type_name

if TYPE_CHECKING:
    from ..schema.definition import Definition
    from ..schema.definition_info import DefinitionInfo
    from ..schema.property_definition import PropertyDefinition
    from .scalar_token import ScalarToken
    from .mapping_token import MappingToken
    from .sequence_token import SequenceToken
    from .boolean_token import BooleanToken
    from .null_token import NullToken
    from .number_token import NumberToken
    from .string_token import StringToken


class TemplateTokenError(Exception):
    def __init__(self, message: str, token: "TemplateToken | None" = None) -> None:
        super().__init__(message)
        self.token = token


class TemplateToken(ABC):
    """Base class for all template tokens."""

    def __init__(
        self,
        token_type: TokenType,
        file: int | None,
        range: TokenRange | None,
        definition_info: "DefinitionInfo | None",
    ) -> None:
        self._type = token_type
        self.file = file
        self.range = range
        self.definition_info: "DefinitionInfo | None" = definition_info
        self.property_definition: "PropertyDefinition | None" = None
        self._description: str | None = None

    @property
    def template_token_type(self) -> TokenType:
        return self._type

    @property
    def line(self) -> int | None:
        return self.range.start.line if self.range else None

    @property
    def col(self) -> int | None:
        return self.range.start.column if self.range else None

    @property
    def definition(self) -> "Definition | None":
        return self.definition_info.definition if self.definition_info else None

    @property
    def description(self) -> str | None:
        if self._description is not None:
            return self._description
        if self.property_definition and self.property_definition.description:
            return self.property_definition.description
        return self.definition.description if self.definition else None

    @description.setter
    def description(self, value: str | None) -> None:
        self._description = value

    @property
    @abstractmethod
    def is_scalar(self) -> bool: ...

    @property
    @abstractmethod
    def is_literal(self) -> bool: ...

    @property
    @abstractmethod
    def is_expression(self) -> bool: ...

    @abstractmethod
    def clone(self, omit_source: bool = False) -> "TemplateToken": ...

    def type_name(self) -> str:
        return token_type_name(self._type)

    def assert_null(self, object_description: str) -> "NullToken":
        if self._type == TokenType.Null:
            from .null_token import NullToken

            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type '{token_type_name(TokenType.Null)}' was expected.",
            self,
        )

    def assert_boolean(self, object_description: str) -> "BooleanToken":
        if self._type == TokenType.Boolean:
            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type '{token_type_name(TokenType.Boolean)}' was expected.",
            self,
        )

    def assert_number(self, object_description: str) -> "NumberToken":
        if self._type == TokenType.Number:
            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type '{token_type_name(TokenType.Number)}' was expected.",
            self,
        )

    def assert_string(self, object_description: str) -> "StringToken":
        if self._type == TokenType.String:
            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type '{token_type_name(TokenType.String)}' was expected.",
            self,
        )

    def assert_scalar(self, object_description: str) -> "ScalarToken":
        if self.is_scalar:
            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type 'ScalarToken' was expected.",
            self,
        )

    def assert_sequence(self, object_description: str) -> "SequenceToken":
        if self._type == TokenType.Sequence:
            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type '{token_type_name(TokenType.Sequence)}' was expected.",
            self,
        )

    def assert_mapping(self, object_description: str) -> "MappingToken":
        if self._type == TokenType.Mapping:
            return self  # type: ignore[return-value]
        raise TemplateTokenError(
            f"Unexpected type '{self.type_name()}' encountered while reading "
            f"'{object_description}'. The type '{token_type_name(TokenType.Mapping)}' was expected.",
            self,
        )

    @staticmethod
    def traverse(
        value: "TemplateToken",
        omit_keys: bool = False,
    ) -> Generator[
        tuple[
            "TemplateToken | None",
            "TemplateToken",
            "TemplateToken | None",
            list["TemplateToken"],
        ],
        None,
        None,
    ]:
        """Depth-first traversal of the token tree.

        Yields (parent, token, key_token, ancestors) for each token.
        """
        from .traversal_state import TraversalState

        yield (None, value, None, [])

        if value.template_token_type not in (TokenType.Sequence, TokenType.Mapping):
            return

        state: TraversalState | None = TraversalState(None, value)
        state = TraversalState(state, value)
        while state.parent is not None:
            if state.move_next(omit_keys):
                value = state.current  # type: ignore[assignment]
                yield (
                    state.parent.current,
                    value,
                    state.current_key,
                    state.get_ancestors(),
                )
                if value.template_token_type in (TokenType.Sequence, TokenType.Mapping):
                    state = TraversalState(state, value)
            else:
                state = state.parent

    def to_json(self) -> object:
        return None
