"""convert_to_actions_environment_ref — converts an environment token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....tokens.template_token import TemplateToken
from ....tokens.type_guards import is_scalar
from ...workflow_template import ActionsEnvironmentReference

if TYPE_CHECKING:
    from ....templates.template_context import TemplateContext


def convert_to_actions_environment_ref(
    context: "TemplateContext",
    token: TemplateToken,
) -> ActionsEnvironmentReference:
    result = ActionsEnvironmentReference()

    if token.is_expression:
        return result

    if is_scalar(token):
        result.name = token
        return result

    environment_mapping = token.assert_mapping("job environment")
    for prop in environment_mapping:
        prop_name = prop.key.assert_string("job environment key")
        if prop.key.is_expression or prop.value.is_expression:
            continue

        if prop_name.value == "name":
            result.name = prop.value.assert_scalar("job environment name key")
        elif prop_name.value == "url":
            result.url = prop.value
        elif prop_name.value == "deployment":
            deployment_value = prop.value.assert_boolean("job environment deployment")
            if deployment_value.value is False:
                result.skip_deployment = True

    return result
