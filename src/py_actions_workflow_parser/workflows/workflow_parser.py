"""parse_workflow — parses a GitHub Actions workflow YAML file."""

from __future__ import annotations

from typing import Union

from ..templates.template_context import TemplateContext, TemplateValidationErrors
from ..templates.template_parse_result import TemplateParseResult
from ..templates.template_reader import read_template
from ..templates.trace_writer import TraceWriter
from .file import File
from .workflow_constants import WORKFLOW_ROOT
from .workflow_schema import get_workflow_schema
from .yaml_object_reader import YamlObjectReader

# Backwards-compatible type alias
ParseWorkflowResult = TemplateParseResult


def parse_workflow(
    entry_file: File,
    context_or_trace: Union[TraceWriter, TemplateContext],
) -> TemplateParseResult:
    """Parse a GitHub Actions workflow YAML and return the template parse result."""
    if isinstance(context_or_trace, TemplateContext):
        context = context_or_trace
    else:
        context = TemplateContext(
            TemplateValidationErrors(),
            get_workflow_schema(),
            context_or_trace,
        )

    file_id = context.get_file_id(entry_file.name)
    reader = YamlObjectReader(file_id, entry_file.content)

    if reader.errors:
        # The file is not valid YAML — template errors would be misleading
        for err in reader.errors:
            context.error(file_id, err.message, err.range)
        return TemplateParseResult(context, None)

    result = read_template(context, WORKFLOW_ROOT, reader, file_id)
    return TemplateParseResult(context, result)
