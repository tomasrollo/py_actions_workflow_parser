"""Type guards for workflow template types."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow_template import (
        ActionStep,
        Job,
        ReusableWorkflowJob,
        RunStep,
        Step,
        WorkflowJob,
    )


def is_run_step(step: "Step") -> "bool":
    from .workflow_template import RunStep as _RunStep

    return isinstance(step, _RunStep) and step.run is not None


def is_action_step(step: "Step") -> "bool":
    from .workflow_template import ActionStep as _ActionStep

    return isinstance(step, _ActionStep) and step.uses is not None


def is_job(job: "WorkflowJob") -> "bool":
    return job.type == "job"


def is_reusable_workflow_job(job: "WorkflowJob") -> "bool":
    return job.type == "reusableWorkflowJob"
