"""action_template — ActionTemplate dataclass and convert_action_template()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Union

from ..model.converter.if_condition import (
    convert_to_if_condition,
    validate_runs_if_condition,
)
from ..model.workflow_template import ActionStep, RunStep, Step
from ..tokens.basic_expression_token import BasicExpressionToken
from ..tokens.mapping_token import MappingToken
from ..tokens.scalar_token import ScalarToken
from ..tokens.string_token import StringToken
from ..tokens.template_token import TemplateToken
from ..tokens.type_guards import (
    is_boolean,
    is_mapping,
    is_scalar,
    is_sequence,
    is_string,
)

if TYPE_CHECKING:
    from ..templates.template_context import TemplateContext


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ActionInputDefinition:
    id: str = ""
    description: Optional[str] = None
    required: Optional[bool] = None
    default: Optional[ScalarToken] = None
    deprecation_message: Optional[str] = None  # "deprecationMessage"


@dataclass
class ActionOutputDefinition:
    id: str = ""
    description: Optional[str] = None
    value: Optional[ScalarToken] = None


@dataclass
class ActionRunsComposite:
    using: str = "composite"
    steps: list[Step] = field(default_factory=list)


@dataclass
class ActionRunsNode:
    using: str = "node20"  # node12 | node16 | node20 | node24
    main: str = ""
    pre: Optional[str] = None
    pre_if: Optional[str] = None  # "pre-if"
    post: Optional[str] = None
    post_if: Optional[str] = None  # "post-if"


@dataclass
class ActionRunsDocker:
    using: str = "docker"
    image: str = ""
    pre_entrypoint: Optional[str] = None  # "pre-entrypoint"
    pre_if: Optional[str] = None  # "pre-if"
    entrypoint: Optional[str] = None
    post_entrypoint: Optional[str] = None  # "post-entrypoint"
    post_if: Optional[str] = None  # "post-if"
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None


ActionRuns = Union[ActionRunsComposite, ActionRunsNode, ActionRunsDocker]


@dataclass
class ActionBranding:
    icon: Optional[str] = None
    color: Optional[str] = None


@dataclass
class ActionTemplate:
    name: str = ""
    description: str = ""
    author: Optional[str] = None
    inputs: Optional[list[ActionInputDefinition]] = None
    outputs: Optional[list[ActionOutputDefinition]] = None
    runs: Optional[ActionRuns] = None
    branding: Optional[ActionBranding] = None


@dataclass
class ActionTemplateConverterOptions:
    error_policy: Optional[str] = None  # "ReturnErrorsOnly" | "TryConversion"


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

_NODE_RUNTIMES = {"node12", "node16", "node20", "node24"}


def convert_action_template(
    context: "TemplateContext",
    root: TemplateToken,
    options: Optional[ActionTemplateConverterOptions] = None,
) -> ActionTemplate:
    """Convert a parsed action template token tree into an ActionTemplate."""
    result = ActionTemplate()
    error_policy = (options.error_policy if options else None) or "ReturnErrorsOnly"

    # Skip conversion if there are parse errors (unless TryConversion is set)
    if context.errors.get_errors() and error_policy == "ReturnErrorsOnly":
        return result

    if not is_mapping(root):
        context.error(root, Exception("Action must be a mapping"))
        return result

    for item in root:
        key = item.key.assert_string("action key")

        if key.value == "name":
            if is_string(item.value):
                result.name = item.value.value
        elif key.value == "description":
            if is_string(item.value):
                result.description = item.value.value
        elif key.value == "author":
            if is_string(item.value):
                result.author = item.value.value
        elif key.value == "inputs":
            result.inputs = _convert_inputs(context, item.value)
        elif key.value == "outputs":
            result.outputs = _convert_outputs(context, item.value)
        elif key.value == "runs":
            result.runs = _convert_runs(context, item.value)
        elif key.value == "branding":
            result.branding = _convert_branding(context, item.value)

    return result


def _convert_inputs(
    context: "TemplateContext",
    token: TemplateToken,
) -> list[ActionInputDefinition]:
    inputs: list[ActionInputDefinition] = []
    if not is_mapping(token):
        return inputs

    for item in token:
        input_id = item.key.assert_string("input id").value
        inp = ActionInputDefinition(id=input_id)

        if is_mapping(item.value):
            for prop in item.value:
                prop_key = prop.key.assert_string("input property").value

                if prop_key == "description":
                    if is_string(prop.value):
                        inp.description = prop.value.value
                elif prop_key == "required":
                    if is_boolean(prop.value):
                        inp.required = prop.value.value
                    elif is_string(prop.value):
                        inp.required = prop.value.value.lower() == "true"
                elif prop_key == "default":
                    if is_scalar(prop.value):
                        inp.default = prop.value  # type: ignore[assignment]
                elif prop_key == "deprecationMessage":
                    if is_string(prop.value):
                        inp.deprecation_message = prop.value.value

        inputs.append(inp)

    return inputs


def _convert_outputs(
    context: "TemplateContext",
    token: TemplateToken,
) -> list[ActionOutputDefinition]:
    outputs: list[ActionOutputDefinition] = []
    if not is_mapping(token):
        return outputs

    for item in token:
        output_id = item.key.assert_string("output id").value
        out = ActionOutputDefinition(id=output_id)

        if is_mapping(item.value):
            for prop in item.value:
                prop_key = prop.key.assert_string("output property").value

                if prop_key == "description":
                    if is_string(prop.value):
                        out.description = prop.value.value
                elif prop_key == "value":
                    if is_scalar(prop.value):
                        out.value = prop.value  # type: ignore[assignment]

        outputs.append(out)

    return outputs


def _convert_runs(
    context: "TemplateContext",
    token: TemplateToken,
) -> ActionRuns:
    if not is_mapping(token):
        return ActionRunsComposite()

    using: Optional[str] = None
    main: Optional[str] = None
    image: Optional[str] = None
    pre: Optional[str] = None
    pre_if: Optional[str] = None
    post: Optional[str] = None
    post_if: Optional[str] = None
    pre_entrypoint: Optional[str] = None
    entrypoint: Optional[str] = None
    post_entrypoint: Optional[str] = None
    args: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    steps: list[Step] = []

    for item in token:
        key = item.key.assert_string("runs property").value

        if key == "using":
            if is_string(item.value):
                using = item.value.value
        elif key == "main":
            if is_string(item.value):
                main = item.value.value
        elif key == "image":
            if is_string(item.value):
                image = item.value.value
        elif key == "pre":
            if is_string(item.value):
                pre = item.value.value
        elif key == "pre-if":
            if is_string(item.value):
                pre_if = validate_runs_if_condition(
                    context, item.value, item.value.value
                )
        elif key == "post":
            if is_string(item.value):
                post = item.value.value
        elif key == "post-if":
            if is_string(item.value):
                post_if = validate_runs_if_condition(
                    context, item.value, item.value.value
                )
        elif key == "pre-entrypoint":
            if is_string(item.value):
                pre_entrypoint = item.value.value
        elif key == "entrypoint":
            if is_string(item.value):
                entrypoint = item.value.value
        elif key == "post-entrypoint":
            if is_string(item.value):
                post_entrypoint = item.value.value
        elif key == "args":
            if is_sequence(item.value):
                args = []
                for arg in item.value:
                    if is_scalar(arg):
                        args.append(str(arg))
        elif key == "env":
            if is_mapping(item.value):
                env = {}
                for env_item in item.value:
                    env_key = env_item.key.assert_string("env key").value
                    if is_string(env_item.value):
                        env[env_key] = env_item.value.value
        elif key == "steps":
            steps = _convert_steps(context, item.value)

    if using == "composite":
        return ActionRunsComposite(using="composite", steps=steps)
    elif using == "docker" and image:
        return ActionRunsDocker(
            using="docker",
            image=image,
            pre_entrypoint=pre_entrypoint,
            pre_if=pre_if,
            entrypoint=entrypoint,
            post_entrypoint=post_entrypoint,
            post_if=post_if,
            args=args,
            env=env,
        )
    elif using in _NODE_RUNTIMES and main:
        return ActionRunsNode(
            using=using,
            main=main,
            pre=pre,
            pre_if=pre_if,
            post=post,
            post_if=post_if,
        )

    # Default fallback
    return ActionRunsComposite()


def _convert_steps(
    context: "TemplateContext",
    token: TemplateToken,
) -> list[Step]:
    steps: list[Step] = []
    if not is_sequence(token):
        return steps

    for step_token in token:
        if not is_mapping(step_token):
            continue
        step = _convert_step(context, step_token)
        if step is not None:
            steps.append(step)

    return steps


_DEFAULT_IF = BasicExpressionToken(None, None, "success()", None, None, None)


def _convert_step(
    context: "TemplateContext",
    token: MappingToken,
) -> Optional[Step]:
    step_id: Optional[str] = None
    name: Optional[ScalarToken] = None
    if_condition: Optional[BasicExpressionToken] = None
    continue_on_error: Optional[Union[bool, ScalarToken]] = None
    env: Optional[MappingToken] = None
    run: Optional[ScalarToken] = None
    uses: Optional[StringToken] = None

    for item in token:
        key = item.key.assert_string("step property").value

        if key == "id":
            if is_string(item.value):
                step_id = item.value.value
        elif key == "name":
            if is_scalar(item.value):
                name = item.value  # type: ignore[assignment]
        elif key == "if":
            if_condition = convert_to_if_condition(context, item.value)
        elif key == "continue-on-error":
            if is_boolean(item.value):
                continue_on_error = item.value.value
            elif is_scalar(item.value):
                continue_on_error = item.value  # type: ignore[assignment]
        elif key == "env":
            if is_mapping(item.value):
                env = item.value
        elif key == "run":
            if is_scalar(item.value):
                run = item.value  # type: ignore[assignment]
        elif key == "uses":
            if is_string(item.value):
                uses = item.value

    effective_if = if_condition or _DEFAULT_IF

    if run is not None:
        step = RunStep(id=step_id or "", name=name, if_condition=effective_if)
        step.continue_on_error = continue_on_error
        step.env = env
        step.run = run
        return step
    elif uses is not None:
        step = ActionStep(id=step_id or "", name=name, if_condition=effective_if)
        step.continue_on_error = continue_on_error
        step.env = env
        step.uses = uses
        return step

    return None


def _convert_branding(
    context: "TemplateContext",
    token: TemplateToken,
) -> ActionBranding:
    branding = ActionBranding()
    if not is_mapping(token):
        return branding

    for item in token:
        key = item.key.assert_string("branding property").value
        if key == "icon":
            if is_string(item.value):
                branding.icon = item.value.value
        elif key == "color":
            if is_string(item.value):
                branding.color = item.value.value

    return branding
