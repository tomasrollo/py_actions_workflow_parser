"""Workflow data model — typed dataclasses for the parsed workflow structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

from ..tokens.basic_expression_token import BasicExpressionToken
from ..tokens.mapping_token import MappingToken
from ..tokens.scalar_token import ScalarToken
from ..tokens.sequence_token import SequenceToken
from ..tokens.string_token import StringToken
from ..tokens.template_token import TemplateToken


# ---------------------------------------------------------------------------
# Simple filter configs (event-level)
# ---------------------------------------------------------------------------


@dataclass
class TypesFilterConfig:
    types: Optional[list[str]] = None


@dataclass
class VersionsFilterConfig:
    versions: Optional[list[str]] = None


@dataclass
class NamesFilterConfig:
    names: Optional[list[str]] = None


@dataclass
class BranchFilterConfig:
    branches: Optional[list[str]] = None
    branches_ignore: Optional[list[str]] = None  # "branches-ignore"


@dataclass
class TagFilterConfig:
    tags: Optional[list[str]] = None
    tags_ignore: Optional[list[str]] = None  # "tags-ignore"


@dataclass
class PathFilterConfig:
    paths: Optional[list[str]] = None
    paths_ignore: Optional[list[str]] = None  # "paths-ignore"


@dataclass
class WorkflowFilterConfig:
    workflows: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Input / secret / schedule config
# ---------------------------------------------------------------------------


class InputType(str, Enum):
    string = "string"
    choice = "choice"
    boolean = "boolean"
    environment = "environment"
    number = "number"


@dataclass
class InputConfig:
    type: InputType = InputType.string
    description: Optional[str] = None
    required: Optional[bool] = None
    default: Optional[Union[str, bool, float, ScalarToken]] = None
    options: Optional[list[str]] = None


@dataclass
class SecretConfig:
    description: Optional[str] = None
    required: Optional[bool] = None


@dataclass
class ScheduleConfig:
    cron: str = ""
    timezone: Optional[str] = None


# ---------------------------------------------------------------------------
# workflow_dispatch / workflow_call configs
# ---------------------------------------------------------------------------


@dataclass
class WorkflowDispatchConfig:
    inputs: Optional[dict[str, InputConfig]] = None


@dataclass
class WorkflowCallConfig:
    inputs: Optional[dict[str, InputConfig]] = None
    secrets: Optional[dict[str, SecretConfig]] = None


# ---------------------------------------------------------------------------
# EventsConfig — all trigger events
# ---------------------------------------------------------------------------


@dataclass
class EventsConfig:
    schedule: Optional[list[ScheduleConfig]] = None
    workflow_dispatch: Optional[WorkflowDispatchConfig] = None
    workflow_call: Optional[WorkflowCallConfig] = None

    pull_request: Optional[dict[str, Any]] = (
        None  # BranchFilterConfig & PathFilterConfig & TypesFilterConfig
    )
    pull_request_target: Optional[dict[str, Any]] = None
    push: Optional[dict[str, Any]] = (
        None  # BranchFilterConfig & TagFilterConfig & PathFilterConfig
    )
    workflow_run: Optional[dict[str, Any]] = (
        None  # WorkflowFilterConfig & BranchFilterConfig & TypesFilterConfig
    )

    # All other event names → stored in the extra dict
    extra: dict[str, Any] = field(default_factory=dict)

    # Insertion order of event names (for deterministic serialization)
    event_order: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@dataclass
class BaseStep:
    id: str = ""
    name: Optional[ScalarToken] = None
    if_condition: Optional[BasicExpressionToken] = None  # "if"
    continue_on_error: Optional[Union[bool, ScalarToken]] = None  # "continue-on-error"
    env: Optional[MappingToken] = None
    timeout_minutes: Optional[ScalarToken] = None  # "timeout-minutes"


@dataclass
class RunStep(BaseStep):
    run: Optional[ScalarToken] = None
    working_directory: Optional[ScalarToken] = None  # "working-directory"
    shell: Optional[ScalarToken] = None


@dataclass
class ActionStep(BaseStep):
    uses: Optional[StringToken] = None
    with_: Optional[MappingToken] = None  # "with"


Step = Union[RunStep, ActionStep]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@dataclass
class BaseJob:
    type: str = ""
    id: Optional[StringToken] = None
    name: Optional[ScalarToken] = None
    needs: Optional[list[StringToken]] = None
    if_condition: Optional[BasicExpressionToken] = None  # "if"
    permissions: Optional[dict[str, str]] = None
    strategy: Optional[TemplateToken] = None
    concurrency: Optional[TemplateToken] = None
    outputs: Optional[MappingToken] = None
    snapshot: Optional[TemplateToken] = None


@dataclass
class Job(BaseJob):
    type: str = "job"
    continue_on_error: Optional[Union[bool, TemplateToken]] = (
        None  # "continue-on-error"
    )
    timeout_minutes: Optional[TemplateToken] = None  # "timeout-minutes"
    cancel_timeout_minutes: Optional[TemplateToken] = None  # "cancel-timeout-minutes"
    env: Optional[MappingToken] = None
    environment: Optional[TemplateToken] = None
    defaults: Optional[MappingToken] = None
    runs_on: Optional[TemplateToken] = None  # "runs-on"
    container: Optional[TemplateToken] = None
    services: Optional[TemplateToken] = None
    steps: list[Step] = field(default_factory=list)


@dataclass
class ReusableWorkflowJob(BaseJob):
    type: str = "reusableWorkflowJob"
    ref: Optional[StringToken] = None
    input_definitions: Optional[MappingToken] = None  # "input-definitions"
    input_values: Optional[MappingToken] = None  # "input-values"
    secret_definitions: Optional[MappingToken] = None  # "secret-definitions"
    secret_values: Optional[MappingToken] = None  # "secret-values"
    inherit_secrets: Optional[bool] = None  # "inherit-secrets"
    jobs: Optional[list["WorkflowJob"]] = None


WorkflowJob = Union[Job, ReusableWorkflowJob]


# ---------------------------------------------------------------------------
# Concurrency / environment
# ---------------------------------------------------------------------------


@dataclass
class ConcurrencySetting:
    group: Optional[StringToken] = None
    cancel_in_progress: Optional[bool] = None  # "cancel-in-progress"


@dataclass
class Credential:
    username: Optional[StringToken] = None
    password: Optional[StringToken] = None


@dataclass
class Container:
    image: Optional[StringToken] = None
    credentials: Optional[Credential] = None
    env: Optional[MappingToken] = None
    ports: Optional[SequenceToken] = None
    volumes: Optional[SequenceToken] = None
    options: Optional[StringToken] = None


@dataclass
class ActionsEnvironmentReference:
    name: Optional[TemplateToken] = None
    url: Optional[TemplateToken] = None
    skip_deployment: Optional[bool] = None  # "skipDeployment"


# ---------------------------------------------------------------------------
# Top-level WorkflowTemplate
# ---------------------------------------------------------------------------


@dataclass
class WorkflowTemplate:
    events: Optional[EventsConfig] = None
    permissions: Optional[dict[str, str]] = None
    defaults: Optional[MappingToken] = None
    jobs: list[WorkflowJob] = field(default_factory=list)
    concurrency: Optional[TemplateToken] = None
    env: Optional[TemplateToken] = None
    errors: Optional[list[dict[str, str]]] = None
