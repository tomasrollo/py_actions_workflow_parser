"""serialize — JSON serialization of WorkflowTemplate matching the TS output format."""

from __future__ import annotations

import json
import math
from typing import Any

from ..tokens.basic_expression_token import BasicExpressionToken
from ..tokens.boolean_token import BooleanToken
from ..tokens.insert_expression_token import InsertExpressionToken
from ..tokens.mapping_token import MappingToken
from ..tokens.null_token import NullToken
from ..tokens.number_token import NumberToken
from ..tokens.sequence_token import SequenceToken
from ..tokens.string_token import StringToken
from ..tokens.template_token import TemplateToken
from ..tokens.types import TokenType
from .type_guards import is_action_step, is_run_step, is_reusable_workflow_job
from .workflow_template import (
    ActionStep,
    EventsConfig,
    InputConfig,
    Job,
    ReusableWorkflowJob,
    RunStep,
    SecretConfig,
    Step,
    WorkflowJob,
    WorkflowTemplate,
)

# Sentinel: use this when value should be omitted (not even None/null)
_OMIT = object()


def _serialize_token(token: TemplateToken | None) -> Any:
    """Convert a TemplateToken to a JSON-serializable value, matching TS toJSON()."""
    if token is None:
        return _OMIT

    if isinstance(token, StringToken):
        return token.value

    if isinstance(token, NullToken):
        return None  # JSON null

    if isinstance(token, BooleanToken):
        return token.value

    if isinstance(token, NumberToken):
        v = token.value
        # Match TypeScript number formatting
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "Infinity" if v > 0 else "-Infinity"
        return v

    if isinstance(token, BasicExpressionToken):
        return {"type": int(TokenType.BasicExpression), "expr": token.expression}

    if isinstance(token, InsertExpressionToken):
        return {"type": int(TokenType.InsertExpression), "expr": "insert"}

    if isinstance(token, MappingToken):
        items = []
        for kv in token:
            key_val = _serialize_token(kv.key)
            value_val = _serialize_token(kv.value)
            item: dict[str, Any] = {"Key": key_val}
            if value_val is not _OMIT:
                item["Value"] = value_val
            else:
                item["Value"] = None
            items.append(item)
        return {"type": int(TokenType.Mapping), "map": items}

    if isinstance(token, SequenceToken):
        return {
            "type": int(TokenType.Sequence),
            "seq": [_serialize_token(t) for t in token],
        }

    return _OMIT


def _add(d: dict, key: str, value: Any) -> None:
    """Add key to dict if value is not _OMIT sentinel."""
    if value is not _OMIT and value is not None:
        d[key] = value
    elif value is None and value is not _OMIT:
        # explicit null
        d[key] = None


def _add_bool_or_token(d: dict, key: str, value: Any) -> None:
    """Add key for bool-or-TemplateToken fields."""
    if value is None:
        return
    if isinstance(value, bool):
        d[key] = value
    elif isinstance(value, TemplateToken):
        sv = _serialize_token(value)
        if sv is not _OMIT:
            d[key] = sv


def _serialize_step(step: Step) -> dict[str, Any]:
    d: dict[str, Any] = {}

    # id is always present (might be empty string)
    d["id"] = step.id

    # name (if present)
    if step.name is not None:
        sv = _serialize_token(step.name)
        if sv is not _OMIT:
            d["name"] = sv

    # if (always present)
    if step.if_condition is not None:
        d["if"] = _serialize_token(step.if_condition)

    # continue-on-error
    _add_bool_or_token(d, "continue-on-error", step.continue_on_error)

    # timeout-minutes
    if step.timeout_minutes is not None:
        sv = _serialize_token(step.timeout_minutes)
        if sv is not _OMIT:
            d["timeout-minutes"] = sv

    # env
    if step.env is not None:
        sv = _serialize_token(step.env)
        if sv is not _OMIT:
            d["env"] = sv

    if is_run_step(step):
        # working-directory
        if step.working_directory is not None:
            sv = _serialize_token(step.working_directory)
            if sv is not _OMIT:
                d["working-directory"] = sv
        # shell
        if step.shell is not None:
            sv = _serialize_token(step.shell)
            if sv is not _OMIT:
                d["shell"] = sv
        # run
        if step.run is not None:
            sv = _serialize_token(step.run)
            if sv is not _OMIT:
                d["run"] = sv

    elif is_action_step(step):
        # uses
        if step.uses is not None:
            sv = _serialize_token(step.uses)
            if sv is not _OMIT:
                d["uses"] = sv
        # with
        if step.with_ is not None:
            sv = _serialize_token(step.with_)
            if sv is not _OMIT:
                d["with"] = sv

    return d


def _serialize_job(job: WorkflowJob) -> dict[str, Any]:
    d: dict[str, Any] = {}
    d["type"] = job.type

    # id
    if job.id is not None:
        d["id"] = _serialize_token(job.id)

    # name
    if job.name is not None:
        sv = _serialize_token(job.name)
        if sv is not _OMIT:
            d["name"] = sv

    # needs (always present — empty list when no dependencies)
    if job.needs is not None:
        d["needs"] = [_serialize_token(n) for n in job.needs]

    # if (always present)
    if job.if_condition is not None:
        d["if"] = _serialize_token(job.if_condition)

    # permissions
    if job.permissions is not None:
        d["permissions"] = job.permissions

    if is_reusable_workflow_job(job):
        _serialize_reusable_job_fields(d, job)
    else:
        _serialize_regular_job_fields(d, job)

    return d


def _serialize_regular_job_fields(d: dict[str, Any], job: Job) -> None:
    # strategy
    if job.strategy is not None:
        sv = _serialize_token(job.strategy)
        if sv is not _OMIT:
            d["strategy"] = sv

    # continue-on-error
    _add_bool_or_token(d, "continue-on-error", job.continue_on_error)

    # timeout-minutes
    if job.timeout_minutes is not None:
        sv = _serialize_token(job.timeout_minutes)
        if sv is not _OMIT:
            d["timeout-minutes"] = sv

    # cancel-timeout-minutes
    if job.cancel_timeout_minutes is not None:
        sv = _serialize_token(job.cancel_timeout_minutes)
        if sv is not _OMIT:
            d["cancel-timeout-minutes"] = sv

    # concurrency
    if job.concurrency is not None:
        sv = _serialize_token(job.concurrency)
        if sv is not _OMIT:
            d["concurrency"] = sv

    # env
    if job.env is not None:
        sv = _serialize_token(job.env)
        if sv is not _OMIT:
            d["env"] = sv

    # environment
    if job.environment is not None:
        sv = _serialize_token(job.environment)
        if sv is not _OMIT:
            d["environment"] = sv

    # defaults
    if job.defaults is not None:
        sv = _serialize_token(job.defaults)
        if sv is not _OMIT:
            d["defaults"] = sv

    # runs-on
    if job.runs_on is not None:
        sv = _serialize_token(job.runs_on)
        if sv is not _OMIT:
            d["runs-on"] = sv

    # container
    if job.container is not None:
        sv = _serialize_token(job.container)
        if sv is not _OMIT:
            d["container"] = sv

    # services
    if job.services is not None:
        sv = _serialize_token(job.services)
        if sv is not _OMIT:
            d["services"] = sv

    # outputs
    if job.outputs is not None:
        sv = _serialize_token(job.outputs)
        if sv is not _OMIT:
            d["outputs"] = sv

    # steps (only if job has steps and hasn't been suppressed)
    if job.steps:
        d["steps"] = [_serialize_step(s) for s in job.steps]
    elif hasattr(job, "steps"):
        # include empty steps list
        d["steps"] = []

    # snapshot
    if job.snapshot is not None:
        sv = _serialize_token(job.snapshot)
        if sv is not _OMIT:
            d["snapshot"] = sv


def _serialize_reusable_job_fields(d: dict[str, Any], job: ReusableWorkflowJob) -> None:
    # ref
    if job.ref is not None:
        d["ref"] = _serialize_token(job.ref)

    # input-definitions
    if job.input_definitions is not None:
        sv = _serialize_token(job.input_definitions)
        if sv is not _OMIT:
            d["input-definitions"] = sv

    # input-values
    if job.input_values is not None:
        sv = _serialize_token(job.input_values)
        if sv is not _OMIT:
            d["input-values"] = sv

    # secret-definitions
    if job.secret_definitions is not None:
        sv = _serialize_token(job.secret_definitions)
        if sv is not _OMIT:
            d["secret-definitions"] = sv

    # secret-values
    if job.secret_values is not None:
        sv = _serialize_token(job.secret_values)
        if sv is not _OMIT:
            d["secret-values"] = sv

    # inherit-secrets
    if job.inherit_secrets is not None:
        d["inherit-secrets"] = job.inherit_secrets

    # concurrency
    if job.concurrency is not None:
        sv = _serialize_token(job.concurrency)
        if sv is not _OMIT:
            d["concurrency"] = sv

    # strategy
    if job.strategy is not None:
        sv = _serialize_token(job.strategy)
        if sv is not _OMIT:
            d["strategy"] = sv

    # outputs
    if job.outputs is not None:
        sv = _serialize_token(job.outputs)
        if sv is not _OMIT:
            d["outputs"] = sv

    # jobs (nested loaded workflows)
    if job.jobs is not None:
        d["jobs"] = [_serialize_job(j) for j in job.jobs]


def _serialize_input_config(cfg: InputConfig) -> dict[str, Any]:
    """Serialize a single InputConfig to a JSON-compatible dict."""
    d: dict[str, Any] = {"type": cfg.type.value}
    if cfg.description is not None:
        d["description"] = cfg.description
    if cfg.required is not None:
        d["required"] = cfg.required
    if cfg.options is not None:
        d["options"] = cfg.options
    if cfg.default is not None:
        d["default"] = cfg.default
    return d


def _serialize_secret_config(cfg: SecretConfig) -> dict[str, Any]:
    """Serialize a single SecretConfig to a JSON-compatible dict."""
    d: dict[str, Any] = {}
    if cfg.description is not None:
        d["description"] = cfg.description
    if cfg.required is not None:
        d["required"] = cfg.required
    return d


def serialize_events_config(events: EventsConfig) -> dict[str, Any]:
    """Serialize EventsConfig to a JSON-compatible dict, preserving insertion order."""
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
                        name: _serialize_input_config(cfg)
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
                        name: _serialize_input_config(cfg)
                        for name, cfg in wcc.inputs.items()
                    }
                if wcc.secrets:
                    wc_dict["secrets"] = {
                        name: _serialize_secret_config(cfg)
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


def serialize_workflow_template(
    wt: WorkflowTemplate,
    include_events: bool = False,
) -> dict[str, Any]:
    """
    Produce a JSON-serializable dict from a WorkflowTemplate.

    The key ordering follows the TS implementation's insertion order, which is
    determined by the YAML key order at the root level.
    """
    d: dict[str, Any] = {}

    if include_events and wt.events is not None:
        d["events"] = serialize_events_config(wt.events)

    # If there are errors, omit jobs (per TS test logic)
    if wt.errors:
        d["errors"] = wt.errors
        return d

    # Permissions
    if wt.permissions is not None:
        d["permissions"] = wt.permissions

    # Concurrency
    if wt.concurrency is not None:
        sv = _serialize_token(wt.concurrency)
        if sv is not _OMIT:
            d["concurrency"] = sv

    # Env
    if wt.env is not None:
        sv = _serialize_token(wt.env)
        if sv is not _OMIT:
            d["env"] = sv

    # Defaults
    if wt.defaults is not None:
        sv = _serialize_token(wt.defaults)
        if sv is not _OMIT:
            d["defaults"] = sv

    # Jobs
    d["jobs"] = [_serialize_job(j) for j in (wt.jobs or [])]

    return d


def workflow_template_to_json(
    wt: WorkflowTemplate,
    include_events: bool = False,
) -> str:
    """Serialize WorkflowTemplate to JSON string with 2-space indent (matching TS output)."""
    d = serialize_workflow_template(wt, include_events=include_events)
    return json.dumps(d, indent="  ")
