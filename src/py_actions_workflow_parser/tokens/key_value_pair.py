"""KeyValuePair — a key-value entry in a MappingToken."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scalar_token import ScalarToken
    from .template_token import TemplateToken


class KeyValuePair:
    def __init__(self, key: "ScalarToken", value: "TemplateToken") -> None:
        self.key = key
        self.value = value
