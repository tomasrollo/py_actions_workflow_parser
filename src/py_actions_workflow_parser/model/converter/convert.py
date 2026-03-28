"""convert_workflow_template — top-level workflow conversion entry point."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from ...tokens.template_token import TemplateToken, TemplateTokenError
from ..type_guards import is_reusable_workflow_job
from ..workflow_template import WorkflowTemplate
from .concurrency import convert_concurrency
from .events import convert_on
from .handle_errors import handle_template_token_errors
from .jobs import convert_jobs
from .permissions import convert_permissions

if TYPE_CHECKING:
    from ...templates.template_context import TemplateContext
    from ...workflows.file_provider import FileProvider


class ErrorPolicy(Enum):
    ReturnErrorsOnly = "ReturnErrorsOnly"
    TryConversion = "TryConversion"


class WorkflowTemplateConverterOptions:
    def __init__(
        self,
        *,
        max_reusable_workflow_depth: int = 4,
        fetch_reusable_workflow_depth: int = 0,
        error_policy: ErrorPolicy = ErrorPolicy.ReturnErrorsOnly,
    ) -> None:
        self.max_reusable_workflow_depth = max_reusable_workflow_depth
        self.fetch_reusable_workflow_depth = fetch_reusable_workflow_depth
        self.error_policy = error_policy


_DEFAULT_OPTIONS = WorkflowTemplateConverterOptions()


def convert_workflow_template(
    context: "TemplateContext",
    root: TemplateToken,
    file_provider: "FileProvider | None" = None,
    options: WorkflowTemplateConverterOptions | None = None,
) -> WorkflowTemplate:
    opts = options or _DEFAULT_OPTIONS
    result = WorkflowTemplate()

    if (
        context.errors.get_errors()
        and opts.error_policy == ErrorPolicy.ReturnErrorsOnly
    ):
        result.errors = [{"Message": e.message} for e in context.errors.get_errors()]
        return result

    if file_provider is None and opts.fetch_reusable_workflow_depth > 0:
        context.error(root, "A file provider is required to fetch reusable workflows")

    try:
        root_mapping = root.assert_mapping("root")

        # First pass: extract permissions and jobs token for two-pass processing
        workflow_permissions = None
        jobs_token = None
        for item in root_mapping:
            key_str = item.key.assert_string("root key").value
            if key_str == "permissions":
                workflow_permissions = convert_permissions(item.value)

        for item in root_mapping:
            key = item.key.assert_string("root key")

            if key.value == "on":
                result.events = handle_template_token_errors(
                    root,
                    context,
                    None,
                    lambda v=item.value: convert_on(context, v),
                )

            elif key.value == "jobs":
                result.jobs = (
                    handle_template_token_errors(
                        root,
                        context,
                        [],
                        lambda v=item.value, wp=workflow_permissions: convert_jobs(
                            context, v, wp
                        ),
                    )
                    or []
                )

            elif key.value == "concurrency":
                handle_template_token_errors(
                    root,
                    context,
                    None,
                    lambda v=item.value: convert_concurrency(context, v),
                )
                result.concurrency = item.value

            elif key.value == "env":
                result.env = item.value

            elif key.value == "permissions":
                result.permissions = workflow_permissions

            elif key.value == "defaults":

                def _handle_defaults(v=item.value):
                    nonlocal result
                    result.defaults = v.assert_mapping("root defaults")

                handle_template_token_errors(
                    item.value, context, None, _handle_defaults
                )

        # NOTE: reusable workflow fetching (file_provider) is intentionally not
        # implemented here since convertReferencedWorkflow was not present in the
        # original source tree included in this project.

    except TemplateTokenError as err:
        context.error(err.token, str(err))
    except Exception as err:
        context.error(root, str(err))
    finally:
        if context.errors.get_errors():
            result.errors = [
                {"Message": e.message} for e in context.errors.get_errors()
            ]

    return result
