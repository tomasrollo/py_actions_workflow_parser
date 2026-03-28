"""convert_job — converts a single job mapping token."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...tokens.type_guards import is_sequence, is_string
from ...tokens.template_token import TemplateToken
from ..workflow_template import Job, ReusableWorkflowJob, Step, WorkflowJob
from .concurrency import convert_concurrency
from .container import convert_to_job_container, convert_to_job_services
from .handle_errors import handle_template_token_errors
from .id_builder import IdBuilder
from .if_condition import convert_to_if_condition
from .job.environment import convert_to_actions_environment_ref
from .job.runs_on import convert_runs_on
from .permissions import convert_permissions
from .steps import convert_steps

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext
    from ...tokens.basic_expression_token import BasicExpressionToken
    from ...tokens.mapping_token import MappingToken
    from ...tokens.scalar_token import ScalarToken
    from ...tokens.string_token import StringToken


def convert_job(
    context: "TemplateContext",
    job_key: "StringToken",
    token: "MappingToken",
    workflow_permissions: "dict[str, str] | None" = None,
) -> WorkflowJob:
    error = IdBuilder().try_add_known_id(job_key.value)
    if error:
        context.error(job_key, error)

    concurrency: TemplateToken | None = None
    container: TemplateToken | None = None
    env: "MappingToken | None" = None
    environment: TemplateToken | None = None
    if_condition: "BasicExpressionToken | None" = None
    name: "ScalarToken | None" = None
    outputs: "MappingToken | None" = None
    runs_on: TemplateToken | None = None
    services: TemplateToken | None = None
    strategy: TemplateToken | None = None
    snapshot: TemplateToken | None = None
    needs: "list[StringToken] | None" = None
    steps: list[Step] = []
    workflow_job_ref: "StringToken | None" = None
    workflow_job_inputs: "MappingToken | None" = None
    inherit_secrets = False
    workflow_job_secrets: "MappingToken | None" = None
    defaults: "MappingToken | None" = None
    permissions: "dict[str, str] | None" = None
    has_own_permissions = False
    continue_on_error: "bool | TemplateToken | None" = None
    timeout_minutes: TemplateToken | None = None
    cancel_timeout_minutes: TemplateToken | None = None

    for item in token:
        property_name = item.key.assert_string("job property name")

        if property_name.value == "cancel-timeout-minutes":
            cancel_timeout_minutes = item.value

        elif property_name.value == "concurrency":
            handle_template_token_errors(
                item.value,
                context,
                None,
                lambda v=item.value: convert_concurrency(context, v),
            )
            concurrency = item.value

        elif property_name.value == "container":
            convert_to_job_container(context, item.value)
            container = item.value

        elif property_name.value == "continue-on-error":
            if not item.value.is_expression:
                continue_on_error = item.value.assert_boolean(
                    "job continue-on-error"
                ).value
            else:
                continue_on_error = item.value

        elif property_name.value == "defaults":

            def _handle_defaults(v=item.value):
                nonlocal defaults
                defaults = v.assert_mapping("job defaults")

            handle_template_token_errors(item.value, context, None, _handle_defaults)

        elif property_name.value == "env":

            def _handle_env(v=item.value):
                nonlocal env
                env = v.assert_mapping("job env")

            handle_template_token_errors(item.value, context, None, _handle_env)

        elif property_name.value == "environment":
            handle_template_token_errors(
                item.value,
                context,
                None,
                lambda v=item.value: convert_to_actions_environment_ref(context, v),
            )
            environment = item.value

        elif property_name.value == "if":
            if_condition = convert_to_if_condition(context, item.value)

        elif property_name.value == "name":
            name = item.value.assert_scalar("job name")

        elif property_name.value == "permissions":
            has_own_permissions = True
            permissions = convert_permissions(item.value)

        elif property_name.value == "needs":
            needs = []
            if is_string(item.value):
                job_needs = item.value.assert_string("job needs id")
                needs.append(job_needs)
            elif is_sequence(item.value):
                for seq_item in item.value:
                    job_needs = seq_item.assert_string("job needs id")
                    needs.append(job_needs)

        elif property_name.value == "outputs":

            def _handle_outputs(v=item.value):
                nonlocal outputs
                outputs = v.assert_mapping("job outputs")

            handle_template_token_errors(item.value, context, None, _handle_outputs)

        elif property_name.value == "runs-on":
            handle_template_token_errors(
                item.value,
                context,
                None,
                lambda v=item.value: convert_runs_on(context, v),
            )
            runs_on = item.value

        elif property_name.value == "services":
            convert_to_job_services(context, item.value)
            services = item.value

        elif property_name.value == "snapshot":
            snapshot = item.value

        elif property_name.value == "steps":
            steps = convert_steps(context, item.value)

        elif property_name.value == "strategy":
            strategy = item.value

        elif property_name.value == "timeout-minutes":
            timeout_minutes = item.value

        elif property_name.value == "uses":
            workflow_job_ref = item.value.assert_string("job uses value")

        elif property_name.value == "with":

            def _handle_with(v=item.value):
                nonlocal workflow_job_inputs
                workflow_job_inputs = v.assert_mapping("uses-with value")

            handle_template_token_errors(item.value, context, None, _handle_with)

        elif property_name.value == "secrets":
            if is_string(item.value) and item.value.value == "inherit":
                inherit_secrets = True
            else:

                def _handle_secrets(v=item.value):
                    nonlocal workflow_job_secrets
                    workflow_job_secrets = v.assert_mapping("uses-secrets value")

                handle_template_token_errors(item.value, context, None, _handle_secrets)

    # Inherit workflow-level permissions if no job-level permissions
    if not has_own_permissions:
        permissions = workflow_permissions

    from ...tokens.basic_expression_token import BasicExpressionToken

    default_if = BasicExpressionToken(None, None, "success()", None, None, None)

    if workflow_job_ref is not None:
        return ReusableWorkflowJob(
            type="reusableWorkflowJob",
            id=job_key,
            name=_job_name(name, job_key),
            needs=needs or [],
            if_condition=if_condition or default_if,
            permissions=permissions,
            ref=workflow_job_ref,
            input_definitions=None,
            input_values=workflow_job_inputs,
            secret_definitions=None,
            secret_values=workflow_job_secrets,
            inherit_secrets=inherit_secrets or None,
            outputs=None,
            concurrency=concurrency,
            strategy=strategy,
        )
    else:
        return Job(
            type="job",
            id=job_key,
            name=_job_name(name, job_key),
            needs=needs or [],
            if_condition=if_condition or default_if,
            permissions=permissions,
            strategy=strategy,
            continue_on_error=continue_on_error,
            timeout_minutes=timeout_minutes,
            cancel_timeout_minutes=cancel_timeout_minutes,
            concurrency=concurrency,
            env=env,
            environment=environment,
            defaults=defaults,
            runs_on=runs_on,
            container=container,
            services=services,
            outputs=outputs,
            steps=steps,
            snapshot=snapshot,
        )


def _job_name(
    name: "ScalarToken | None",
    job_key: "StringToken",
) -> "ScalarToken":
    if name is None:
        return job_key
    if is_string(name) and name.value == "":
        return job_key
    return name
