"""export — Plain-dict / JSON export of the typed data model.

Converts WorkflowTemplate and ActionTemplate (results of convert_workflow_template()
and convert_action_template()) into plain, human-readable Python dicts / JSON strings.

Token fields (e.g. env, runs-on, with) are flattened to plain Python values:
  - StringToken        → str
  - BooleanToken       → bool
  - NumberToken        → float
  - NullToken          → None
  - BasicExpressionToken → "${{ <expr> }}"
  - MappingToken       → dict[str, Any]
  - SequenceToken      → list[Any]
"""

from __future__ import annotations

import json
import math
from typing import Any, Union

from ..actions.action_template import (
    ActionBranding,
    ActionInputDefinition,
    ActionOutputDefinition,
    ActionRunsComposite,
    ActionRunsDocker,
    ActionRunsNode,
    ActionTemplate,
)
from ..tokens.basic_expression_token import BasicExpressionToken
from ..tokens.boolean_token import BooleanToken
from ..tokens.insert_expression_token import InsertExpressionToken
from ..tokens.mapping_token import MappingToken
from ..tokens.null_token import NullToken
from ..tokens.number_token import NumberToken
from ..tokens.scalar_token import ScalarToken
from ..tokens.sequence_token import SequenceToken
from ..tokens.string_token import StringToken
from ..tokens.template_token import TemplateToken
from .type_guards import is_action_step, is_reusable_workflow_job, is_run_step
from .workflow_template import (
    EventsConfig,
    InputConfig,
    Job,
    ReusableWorkflowJob,
    SecretConfig,
    Step,
    WorkflowJob,
    WorkflowTemplate,
)


# ---------------------------------------------------------------------------
# Token → plain value
# ---------------------------------------------------------------------------


def _token_to_plain(token: TemplateToken | None) -> Any:
    """Convert any TemplateToken to a plain Python value."""
    if token is None:
        return None

    if isinstance(token, StringToken):
        return token.value

    if isinstance(token, NullToken):
        return None

    if isinstance(token, BooleanToken):
        return token.value

    if isinstance(token, NumberToken):
        v = token.value
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "Infinity" if v > 0 else "-Infinity"
        # Return int when the float has no fractional part
        return int(v) if v == int(v) else v

    if isinstance(token, BasicExpressionToken):
        return f"${{{{ {token.expression} }}}}"

    if isinstance(token, InsertExpressionToken):
        return "${{ insert }}"

    if isinstance(token, MappingToken):
        result: dict[str, Any] = {}
        for kv in token:
            key = _token_to_plain(kv.key)
            value = _token_to_plain(kv.value)
            if key is not None:
                result[str(key)] = value
        return result

    if isinstance(token, SequenceToken):
        return [_token_to_plain(t) for t in token]

    return None


def _scalar_or_token_to_plain(value: Union[str, bool, float, ScalarToken, None]) -> Any:
    """Handle fields that may be a plain Python scalar or a ScalarToken."""
    if value is None:
        return None
    if isinstance(value, TemplateToken):
        return _token_to_plain(value)
    return value


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def _step_to_plain(step: Step) -> dict[str, Any]:
    d: dict[str, Any] = {}

    d["id"] = step.id

    if step.name is not None:
        d["name"] = _token_to_plain(step.name)

    if step.if_condition is not None:
        d["if"] = _token_to_plain(step.if_condition)

    if step.continue_on_error is not None:
        if isinstance(step.continue_on_error, bool):
            d["continue-on-error"] = step.continue_on_error
        else:
            d["continue-on-error"] = _token_to_plain(step.continue_on_error)

    if step.timeout_minutes is not None:
        d["timeout-minutes"] = _token_to_plain(step.timeout_minutes)

    if step.env is not None:
        d["env"] = _token_to_plain(step.env)

    if is_run_step(step):
        if step.working_directory is not None:
            d["working-directory"] = _token_to_plain(step.working_directory)
        if step.shell is not None:
            d["shell"] = _token_to_plain(step.shell)
        if step.run is not None:
            d["run"] = _token_to_plain(step.run)

    elif is_action_step(step):
        if step.uses is not None:
            d["uses"] = _token_to_plain(step.uses)
        if step.with_ is not None:
            d["with"] = _token_to_plain(step.with_)

    return d


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


def _job_to_plain(job: WorkflowJob) -> dict[str, Any]:
    d: dict[str, Any] = {}
    d["type"] = job.type

    if job.id is not None:
        d["id"] = _token_to_plain(job.id)

    if job.name is not None:
        d["name"] = _token_to_plain(job.name)

    if job.needs is not None:
        d["needs"] = [_token_to_plain(n) for n in job.needs]

    if job.if_condition is not None:
        d["if"] = _token_to_plain(job.if_condition)

    if job.permissions is not None:
        d["permissions"] = job.permissions

    if job.strategy is not None:
        d["strategy"] = _token_to_plain(job.strategy)

    if job.concurrency is not None:
        d["concurrency"] = _token_to_plain(job.concurrency)

    if job.outputs is not None:
        d["outputs"] = _token_to_plain(job.outputs)

    if is_reusable_workflow_job(job):
        _reusable_job_to_plain(d, job)
    else:
        _regular_job_to_plain(d, job)

    return d


def _regular_job_to_plain(d: dict[str, Any], job: Job) -> None:
    if job.continue_on_error is not None:
        if isinstance(job.continue_on_error, bool):
            d["continue-on-error"] = job.continue_on_error
        else:
            d["continue-on-error"] = _token_to_plain(job.continue_on_error)

    if job.timeout_minutes is not None:
        d["timeout-minutes"] = _token_to_plain(job.timeout_minutes)

    if job.cancel_timeout_minutes is not None:
        d["cancel-timeout-minutes"] = _token_to_plain(job.cancel_timeout_minutes)

    if job.env is not None:
        d["env"] = _token_to_plain(job.env)

    if job.environment is not None:
        d["environment"] = _token_to_plain(job.environment)

    if job.defaults is not None:
        d["defaults"] = _token_to_plain(job.defaults)

    if job.runs_on is not None:
        d["runs-on"] = _token_to_plain(job.runs_on)

    if job.container is not None:
        d["container"] = _token_to_plain(job.container)

    if job.services is not None:
        d["services"] = _token_to_plain(job.services)

    d["steps"] = [_step_to_plain(s) for s in job.steps]


def _reusable_job_to_plain(d: dict[str, Any], job: ReusableWorkflowJob) -> None:
    if job.ref is not None:
        d["ref"] = _token_to_plain(job.ref)

    if job.input_definitions is not None:
        d["input-definitions"] = _token_to_plain(job.input_definitions)

    if job.input_values is not None:
        d["input-values"] = _token_to_plain(job.input_values)

    if job.secret_definitions is not None:
        d["secret-definitions"] = _token_to_plain(job.secret_definitions)

    if job.secret_values is not None:
        d["secret-values"] = _token_to_plain(job.secret_values)

    if job.inherit_secrets is not None:
        d["inherit-secrets"] = job.inherit_secrets

    if job.jobs is not None:
        d["jobs"] = [_job_to_plain(j) for j in job.jobs]


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def _input_config_to_plain(cfg: InputConfig) -> dict[str, Any]:
    d: dict[str, Any] = {"type": cfg.type.value}
    if cfg.description is not None:
        d["description"] = cfg.description
    if cfg.required is not None:
        d["required"] = cfg.required
    if cfg.default is not None:
        d["default"] = _scalar_or_token_to_plain(cfg.default)
    if cfg.options is not None:
        d["options"] = cfg.options
    return d


def _secret_config_to_plain(cfg: SecretConfig) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if cfg.description is not None:
        d["description"] = cfg.description
    if cfg.required is not None:
        d["required"] = cfg.required
    return d


def events_config_to_plain(events: EventsConfig) -> dict[str, Any]:
    """Serialize EventsConfig to a plain dict, preserving insertion order."""
    d: dict[str, Any] = {}

    for event_name in events.event_order:
        if event_name == "schedule":
            if events.schedule:
                d["schedule"] = [
                    {"cron": s.cron, **({"timezone": s.timezone} if s.timezone else {})}
                    for s in events.schedule
                ]
            else:
                d["schedule"] = []

        elif event_name == "workflow_dispatch":
            wdc = events.workflow_dispatch
            if wdc is None or not wdc.inputs:
                d["workflow_dispatch"] = {}
            else:
                d["workflow_dispatch"] = {
                    "inputs": {
                        name: _input_config_to_plain(cfg)
                        for name, cfg in wdc.inputs.items()
                    }
                }

        elif event_name == "workflow_call":
            wcc = events.workflow_call
            if wcc is None:
                d["workflow_call"] = {}
            else:
                wc_dict: dict[str, Any] = {}
                if wcc.inputs:
                    wc_dict["inputs"] = {
                        name: _input_config_to_plain(cfg)
                        for name, cfg in wcc.inputs.items()
                    }
                if wcc.secrets:
                    wc_dict["secrets"] = {
                        name: _secret_config_to_plain(cfg)
                        for name, cfg in wcc.secrets.items()
                    }
                d["workflow_call"] = wc_dict

        elif event_name == "push":
            d["push"] = events.push or {}
        elif event_name == "pull_request":
            d["pull_request"] = events.pull_request or {}
        elif event_name == "pull_request_target":
            d["pull_request_target"] = events.pull_request_target or {}
        elif event_name == "workflow_run":
            d["workflow_run"] = events.workflow_run or {}
        else:
            d[event_name] = events.extra.get(event_name, {})

    return d


# ---------------------------------------------------------------------------
# WorkflowTemplate
# ---------------------------------------------------------------------------


def workflow_template_to_dict(
    wt: WorkflowTemplate,
    include_events: bool = True,
) -> dict[str, Any]:
    """Convert a WorkflowTemplate to a plain, JSON-serializable dict.

    Args:
        wt: A WorkflowTemplate returned by convert_workflow_template().
        include_events: Whether to include the ``on`` trigger block. Defaults to True.

    Returns:
        A plain dict with all token fields resolved to their Python values.
        Expressions like ``${{ matrix.os }}`` are represented as the string
        ``"${{ matrix.os }}"``.
    """
    d: dict[str, Any] = {}

    if include_events and wt.events is not None:
        d["on"] = events_config_to_plain(wt.events)

    if wt.errors:
        d["errors"] = wt.errors
        return d

    if wt.permissions is not None:
        d["permissions"] = wt.permissions

    if wt.concurrency is not None:
        d["concurrency"] = _token_to_plain(wt.concurrency)

    if wt.env is not None:
        d["env"] = _token_to_plain(wt.env)

    if wt.defaults is not None:
        d["defaults"] = _token_to_plain(wt.defaults)

    d["jobs"] = [_job_to_plain(j) for j in (wt.jobs or [])]

    return d


def workflow_template_to_json(
    wt: WorkflowTemplate,
    include_events: bool = True,
) -> str:
    """Serialize a WorkflowTemplate to a JSON string with 2-space indentation.

    Args:
        wt: A WorkflowTemplate returned by convert_workflow_template().
        include_events: Whether to include the ``on`` trigger block. Defaults to True.

    Returns:
        A JSON string.
    """
    return json.dumps(
        workflow_template_to_dict(wt, include_events=include_events), indent=2
    )


# ---------------------------------------------------------------------------
# ActionTemplate
# ---------------------------------------------------------------------------


def _action_input_to_plain(inp: ActionInputDefinition) -> dict[str, Any]:
    d: dict[str, Any] = {"id": inp.id}
    if inp.description is not None:
        d["description"] = inp.description
    if inp.required is not None:
        d["required"] = inp.required
    if inp.default is not None:
        d["default"] = _token_to_plain(inp.default)
    if inp.deprecation_message is not None:
        d["deprecation-message"] = inp.deprecation_message
    return d


def _action_output_to_plain(out: ActionOutputDefinition) -> dict[str, Any]:
    d: dict[str, Any] = {"id": out.id}
    if out.description is not None:
        d["description"] = out.description
    if out.value is not None:
        d["value"] = _token_to_plain(out.value)
    return d


def _action_runs_to_plain(
    runs: ActionRunsNode | ActionRunsDocker | ActionRunsComposite,
) -> dict[str, Any]:
    d: dict[str, Any] = {"using": runs.using}

    if isinstance(runs, ActionRunsNode):
        d["main"] = runs.main
        if runs.pre is not None:
            d["pre"] = runs.pre
        if runs.pre_if is not None:
            d["pre-if"] = runs.pre_if
        if runs.post is not None:
            d["post"] = runs.post
        if runs.post_if is not None:
            d["post-if"] = runs.post_if

    elif isinstance(runs, ActionRunsDocker):
        d["image"] = runs.image
        if runs.pre_entrypoint is not None:
            d["pre-entrypoint"] = runs.pre_entrypoint
        if runs.pre_if is not None:
            d["pre-if"] = runs.pre_if
        if runs.entrypoint is not None:
            d["entrypoint"] = runs.entrypoint
        if runs.post_entrypoint is not None:
            d["post-entrypoint"] = runs.post_entrypoint
        if runs.post_if is not None:
            d["post-if"] = runs.post_if
        if runs.args is not None:
            d["args"] = runs.args
        if runs.env is not None:
            d["env"] = runs.env

    elif isinstance(runs, ActionRunsComposite):
        d["steps"] = [_step_to_plain(s) for s in runs.steps]

    return d


def _action_branding_to_plain(branding: ActionBranding) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if branding.icon is not None:
        d["icon"] = branding.icon
    if branding.color is not None:
        d["color"] = branding.color
    return d


def action_template_to_dict(at: ActionTemplate) -> dict[str, Any]:
    """Convert an ActionTemplate to a plain, JSON-serializable dict.

    Args:
        at: An ActionTemplate returned by convert_action_template().

    Returns:
        A plain dict with all token fields resolved to their Python values.
    """
    d: dict[str, Any] = {}

    d["name"] = at.name
    d["description"] = at.description

    if at.author is not None:
        d["author"] = at.author

    if at.inputs:
        d["inputs"] = [_action_input_to_plain(inp) for inp in at.inputs]

    if at.outputs:
        d["outputs"] = [_action_output_to_plain(out) for out in at.outputs]

    if at.runs is not None:
        d["runs"] = _action_runs_to_plain(at.runs)

    if at.branding is not None:
        d["branding"] = _action_branding_to_plain(at.branding)

    return d


def action_template_to_json(at: ActionTemplate) -> str:
    """Serialize an ActionTemplate to a JSON string with 2-space indentation.

    Args:
        at: An ActionTemplate returned by convert_action_template().

    Returns:
        A JSON string.
    """
    return json.dumps(action_template_to_dict(at), indent=2)
