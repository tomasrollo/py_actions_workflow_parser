"""convert_concurrency — converts a concurrency token to ConcurrencySetting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...tokens.template_token import TemplateToken
from ...tokens.type_guards import is_string
from ..workflow_template import ConcurrencySetting

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext


def convert_concurrency(
    context: "TemplateContext", token: TemplateToken
) -> ConcurrencySetting:
    result = ConcurrencySetting()

    if token.is_expression:
        return result

    if is_string(token):
        result.group = token  # type: ignore[assignment]
        return result

    concurrency_property = token.assert_mapping("concurrency group")
    for prop in concurrency_property:
        prop_name = prop.key.assert_string("concurrency group key")
        if prop.key.is_expression or prop.value.is_expression:
            continue
        if prop_name.value == "group":
            result.group = prop.value.assert_string("concurrency group")
        elif prop_name.value == "cancel-in-progress":
            result.cancel_in_progress = prop.value.assert_boolean(
                "cancel-in-progress"
            ).value
        else:
            context.error(prop_name, f"Invalid property name: {prop_name.value}")

    return result
