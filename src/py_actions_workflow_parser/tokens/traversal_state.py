"""TraversalState for depth-first token tree traversal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import TokenType

if TYPE_CHECKING:
    from .template_token import TemplateToken


class TraversalState:
    def __init__(self, parent: "TraversalState | None", token: "TemplateToken") -> None:
        self.parent = parent
        self._token = token
        self.current: "TemplateToken | None" = token
        self.current_key: "TemplateToken | None" = None
        self._index = -1
        self._is_key = False

    def move_next(self, omit_keys: bool) -> bool:
        from .sequence_token import SequenceToken
        from .mapping_token import MappingToken

        token_type = self._token.template_token_type

        if token_type == TokenType.Sequence:
            seq = self._token  # type: ignore[assignment]
            self._index += 1
            if self._index < seq.count:  # type: ignore[attr-defined]
                self.current = seq.get(self._index)  # type: ignore[attr-defined]
                return True
            self.current = None
            return False

        if token_type == TokenType.Mapping:
            mapping = self._token  # type: ignore[assignment]

            # Already returned the key, now return the value
            if self._is_key:
                self._is_key = False
                self.current_key = self.current
                self.current = mapping.get(self._index).value  # type: ignore[attr-defined]
                return True

            # Move to next pair
            self._index += 1
            if self._index < mapping.count:  # type: ignore[attr-defined]
                if omit_keys:
                    self._is_key = False
                    self.current_key = mapping.get(self._index).key  # type: ignore[attr-defined]
                    self.current = mapping.get(self._index).value  # type: ignore[attr-defined]
                    return True
                # Return the key first
                self._is_key = True
                self.current_key = None
                self.current = mapping.get(self._index).key  # type: ignore[attr-defined]
                return True

            self.current_key = None
            self.current = None
            return False

        raise ValueError(f"Unexpected token type '{token_type}' when traversing state")

    def get_ancestors(self) -> list["TemplateToken"]:
        ancestors: list[TemplateToken] = []
        state: TraversalState | None = self.parent
        while state is not None:
            if state.current is not None:
                ancestors.insert(0, state.current)
            state = state.parent
        return ancestors
