"""convert_steps — converts the 'steps' token."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ...tokens.template_token import TemplateToken
from ...tokens.type_guards import is_sequence
from ..type_guards import is_action_step
from ..workflow_template import ActionStep, RunStep, Step
from .handle_errors import handle_template_token_errors
from .id_builder import IdBuilder
from .if_condition import convert_to_if_condition

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext
    from ...tokens.basic_expression_token import BasicExpressionToken
    from ...tokens.mapping_token import MappingToken
    from ...tokens.scalar_token import ScalarToken
    from ...tokens.string_token import StringToken


def convert_steps(context: "TemplateContext", steps: TemplateToken) -> list[Step]:
    if not is_sequence(steps):
        context.error(steps, "Invalid format for steps")
        return []

    id_builder = IdBuilder()

    result: list[Step] = []
    for item in steps:
        step = handle_template_token_errors(
            steps, context, None, lambda i=item: _convert_step(context, id_builder, i)
        )
        if step is not None:
            result.append(step)

    # Assign auto-generated IDs to steps that don't have one
    for step in result:
        if step.id:
            continue

        auto_id = ""
        if is_action_step(step):
            auto_id = _create_action_step_id(step)

        if not auto_id:
            auto_id = "run"

        id_builder.append_segment(f"__{auto_id}")
        step.id = id_builder.build()

    return result


def _convert_step(
    context: "TemplateContext",
    id_builder: IdBuilder,
    step: TemplateToken,
) -> Step | None:
    mapping = step.assert_mapping("steps item")

    run: "ScalarToken | None" = None
    step_id: "StringToken | None" = None
    name: "ScalarToken | None" = None
    uses: "StringToken | None" = None
    continue_on_error: "bool | ScalarToken | None" = None
    env: "MappingToken | None" = None
    if_condition: "BasicExpressionToken | None" = None
    timeout_minutes: "ScalarToken | None" = None
    working_directory: "ScalarToken | None" = None
    shell: "ScalarToken | None" = None
    with_: "MappingToken | None" = None

    for item in mapping:
        key = item.key.assert_string("steps item key")

        if key.value == "id":
            step_id = item.value.assert_string("steps item id")
            if step_id:
                error = id_builder.try_add_known_id(step_id.value)
                if error:
                    context.error(step_id, error)

        elif key.value == "name":
            name = item.value.assert_scalar("steps item name")

        elif key.value == "run":
            run = item.value.assert_scalar("steps item run")

        elif key.value == "uses":
            uses = item.value.assert_string("steps item uses")

        elif key.value == "env":
            env = item.value.assert_mapping("step env")

        elif key.value == "if":
            if_condition = convert_to_if_condition(context, item.value)

        elif key.value == "continue-on-error":
            if not item.value.is_expression:
                continue_on_error = item.value.assert_boolean(
                    "steps item continue-on-error"
                ).value
            else:
                continue_on_error = item.value.assert_scalar(
                    "steps item continue-on-error"
                )

        elif key.value == "timeout-minutes":
            timeout_minutes = item.value.assert_scalar("steps item timeout-minutes")

        elif key.value == "working-directory":
            working_directory = item.value.assert_scalar("steps item working-directory")

        elif key.value == "shell":
            shell = item.value.assert_scalar("steps item shell")

        elif key.value == "with":
            with_ = item.value.assert_mapping("steps item with")

    from ...tokens.basic_expression_token import BasicExpressionToken

    default_if = BasicExpressionToken(None, None, "success()", None, None, None)

    if run is not None:
        return RunStep(
            id=step_id.value if step_id else "",
            name=name,
            if_condition=if_condition or default_if,
            continue_on_error=continue_on_error,
            env=env,
            timeout_minutes=timeout_minutes,
            working_directory=working_directory,
            shell=shell,
            run=run,
        )

    if uses is not None:
        return ActionStep(
            id=step_id.value if step_id else "",
            name=name,
            if_condition=if_condition or default_if,
            continue_on_error=continue_on_error,
            env=env,
            timeout_minutes=timeout_minutes,
            uses=uses,
            with_=with_,
        )

    context.error(step, "Expected uses or run to be defined")
    return None


def _create_action_step_id(step: ActionStep) -> str:
    uses = step.uses.value if step.uses else ""

    if uses.startswith("docker://"):
        return uses[len("docker://") :]

    if uses.startswith("./") or uses.startswith(".\\"):
        return "self"

    segments = uses.split("@")
    if len(segments) != 2:
        return ""

    path_segments = [s for s in re.split(r"[/\\]", segments[0]) if s]
    git_ref = segments[1]

    if len(path_segments) >= 2 and path_segments[0] and path_segments[1] and git_ref:
        return f"{path_segments[0]}/{path_segments[1]}"

    return ""
