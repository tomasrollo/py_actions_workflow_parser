"""parse_action — parses a GitHub Actions action.yml file."""

from __future__ import annotations

from typing import Union

from ..templates.template_context import TemplateContext, TemplateValidationErrors
from ..templates.template_parse_result import TemplateParseResult
from ..templates.template_reader import read_template
from ..templates.trace_writer import TraceWriter
from ..workflows.file import File
from ..workflows.yaml_object_reader import YamlObjectReader
from .action_constants import ACTION_ROOT
from .action_schema import get_action_schema


def parse_action(
    entry_file: File,
    context_or_trace: Union[TraceWriter, TemplateContext],
) -> TemplateParseResult:
    """Parse a GitHub Actions action.yml and return the template parse result."""
    if isinstance(context_or_trace, TemplateContext):
        context = context_or_trace
    else:
        context = TemplateContext(
            TemplateValidationErrors(),
            get_action_schema(),
            context_or_trace,
        )

    file_id = context.get_file_id(entry_file.name)
    reader = YamlObjectReader(file_id, entry_file.content)

    if reader.errors:
        # The file is not valid YAML — template errors would be misleading
        for err in reader.errors:
            context.error(file_id, err.message, err.range)
        return TemplateParseResult(context, None)

    result = read_template(context, ACTION_ROOT, reader, file_id)
    return TemplateParseResult(context, result)
