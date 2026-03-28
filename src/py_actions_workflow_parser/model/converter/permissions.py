"""convert_permissions — converts a permissions token to a plain dict."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...tokens.type_guards import is_mapping, is_string

if TYPE_CHECKING:
    from ...tokens.template_token import TemplateToken

# All known permission scopes
_ALL_PERMISSIONS = [
    "actions",
    "checks",
    "contents",
    "deployments",
    "discussions",
    "id-token",
    "issues",
    "packages",
    "pages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
]


def convert_permissions(token: "TemplateToken") -> dict[str, str] | None:
    """Convert a permissions token to {scope: level} dict, filtering 'none' values."""
    if is_string(token):
        if token.value == "read-all":
            return {scope: "read" for scope in _ALL_PERMISSIONS}
        if token.value == "write-all":
            return {scope: "write" for scope in _ALL_PERMISSIONS}
        return None

    if is_mapping(token):
        result: dict[str, str] = {}
        for item in token:
            key = item.key.assert_string("permissions scope")
            value = item.value.assert_string("permissions level")
            if value.value != "none":
                result[key.value] = value.value
        return result

    return None
