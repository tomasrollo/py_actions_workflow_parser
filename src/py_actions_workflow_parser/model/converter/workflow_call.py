"""convert_event_workflow_call — workflow_call event converter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...tokens.mapping_token import MappingToken
from ...tokens.template_token import TemplateToken
from ...tokens.type_guards import is_mapping
from ..workflow_template import InputConfig, InputType, SecretConfig, WorkflowCallConfig
from .string_list import convert_string_list

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext


def convert_event_workflow_call(
    context: "TemplateContext",
    token: MappingToken,
) -> WorkflowCallConfig:
    result = WorkflowCallConfig()
    for item in token:
        key = item.key.assert_string("workflow call input key")
        if key.value == "inputs":
            result.inputs = convert_workflow_inputs(
                context, item.value.assert_mapping("workflow call inputs")
            )
        elif key.value == "secrets":
            result.secrets = _convert_workflow_call_secrets(
                context, item.value.assert_mapping("workflow call secrets")
            )
        elif key.value == "outputs":
            pass  # TODO: outputs support
    return result


def convert_workflow_inputs(
    context: "TemplateContext",
    token: MappingToken,
) -> dict[str, InputConfig]:
    result: dict[str, InputConfig] = {}
    for item in token:
        input_name = item.key.assert_string("input name")
        input_mapping = item.value.assert_mapping("input configuration")
        result[input_name.value] = _convert_workflow_input(context, input_mapping)
    return result


def _convert_workflow_input(
    context: "TemplateContext",
    token: MappingToken,
) -> InputConfig:
    from ...tokens.scalar_token import ScalarToken

    result = InputConfig(type=InputType.string)
    default_value: "ScalarToken | None" = None

    for item in token:
        key = item.key.assert_string("workflow call input key")
        if key.value == "description":
            result.description = item.value.assert_string("input description").value
        elif key.value == "required":
            result.required = item.value.assert_boolean("input required").value
        elif key.value == "default":
            default_value = item.value.assert_scalar("input default")
        elif key.value == "type":
            type_str = item.value.assert_string("input type").value
            try:
                result.type = InputType(type_str)
            except ValueError:
                context.error(item.value, f"Invalid input type '{type_str}'")
        elif key.value == "options":
            result.options = convert_string_list(
                "input options", item.value.assert_sequence("input options")
            )
        else:
            context.error(item.key, f"Invalid key '{key.value}'")

    if default_value is not None and not default_value.is_expression:
        try:
            if result.type == InputType.boolean:
                result.default = default_value.assert_boolean("input default").value
            else:
                result.default = default_value.assert_string("input default").value
        except Exception as err:
            context.error(default_value, err)

    if result.type == InputType.choice:
        if not result.options:
            context.error(token, "Missing 'options' for choice input")
    else:
        if result.options is not None:
            context.error(token, "Input type is not 'choice', but 'options' is defined")

    return result


def _convert_workflow_call_secrets(
    context: "TemplateContext",
    token: MappingToken,
) -> dict[str, SecretConfig]:
    result: dict[str, SecretConfig] = {}
    for item in token:
        secret_name = item.key.assert_string("secret name")
        result[secret_name.value] = _convert_workflow_call_secret(context, item.value)
    return result


def _convert_workflow_call_secret(
    context: "TemplateContext",
    token: TemplateToken,
) -> SecretConfig:
    result = SecretConfig()
    if is_mapping(token):
        for item in token:
            key = item.key.assert_string("workflow call secret key")
            if key.value == "description":
                result.description = item.value.assert_string(
                    "secret description"
                ).value
            elif key.value == "required":
                result.required = item.value.assert_boolean("secret required").value
    return result
