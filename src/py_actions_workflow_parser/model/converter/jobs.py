"""convert_jobs — converts the 'jobs' mapping token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...tokens.template_token import TemplateToken
from ...tokens.type_guards import is_mapping
from ..workflow_template import WorkflowJob
from .handle_errors import handle_template_token_errors
from .convert_job import convert_job

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext
    from ...tokens.string_token import StringToken


def convert_jobs(
    context: "TemplateContext",
    token: TemplateToken,
    workflow_permissions: "dict[str, str] | None" = None,
) -> list[WorkflowJob]:
    if not is_mapping(token):
        context.error(token, "Invalid format for jobs")
        return []

    result: list[WorkflowJob] = []
    jobs_with_satisfied_needs: list[_NodeInfo] = []
    all_jobs_with_unsatisfied_needs: list[_NodeInfo] = []

    for item in token:
        job_key = item.key.assert_string("job name")
        job_def = item.value.assert_mapping(f"job {job_key.value}")

        job = handle_template_token_errors(
            token,
            context,
            None,
            lambda k=job_key, d=job_def: convert_job(
                context, k, d, workflow_permissions
            ),
        )
        if job is not None:
            result.append(job)
            node = _NodeInfo(
                name=job.id.value if job.id else "",
                needs=list(job.needs) if job.needs else [],
            )
            if node.needs:
                all_jobs_with_unsatisfied_needs.append(node)
            else:
                jobs_with_satisfied_needs.append(node)

    _validate_needs(
        token,
        context,
        result,
        jobs_with_satisfied_needs,
        all_jobs_with_unsatisfied_needs,
    )

    return result


class _NodeInfo:
    def __init__(self, name: str, needs: "list[StringToken]") -> None:
        self.name = name
        self.needs = needs


def _validate_needs(
    token: TemplateToken,
    context: "TemplateContext",
    result: list[WorkflowJob],
    jobs_with_satisfied_needs: list[_NodeInfo],
    all_jobs_with_unsatisfied_needs: list[_NodeInfo],
) -> None:
    if not jobs_with_satisfied_needs:
        context.error(
            token, "The workflow must contain at least one job with no dependencies."
        )
        return

    # BFS — topological sort to detect cycles and unknown dependencies
    satisfied = list(jobs_with_satisfied_needs)
    unsatisfied = list(all_jobs_with_unsatisfied_needs)

    while satisfied:
        current_job = satisfied.pop(0)
        for i in range(len(unsatisfied) - 1, -1, -1):
            unsatisfied_job = unsatisfied[i]
            for j in range(len(unsatisfied_job.needs) - 1, -1, -1):
                need = unsatisfied_job.needs[j]
                if need.value == current_job.name:
                    unsatisfied_job.needs.pop(j)
                    if not unsatisfied_job.needs:
                        satisfied.append(unsatisfied_job)
                        unsatisfied.pop(i)

    if unsatisfied:
        job_names = [j.id.value for j in result if j.id]
        for unsatisfied_job in unsatisfied:
            for need in unsatisfied_job.needs:
                if need.value in job_names:
                    context.error(
                        need,
                        f"Job '{unsatisfied_job.name}' depends on job '{need.value}' which creates a cycle in the dependency graph.",
                    )
                else:
                    context.error(
                        need,
                        f"Job '{unsatisfied_job.name}' depends on unknown job '{need.value}'.",
                    )
