"""allowed_context — parse function signature strings from schema context arrays."""

from __future__ import annotations

import re

from py_actions_expressions_parser import FunctionInfo

from .template_constants import MAX_CONSTANT

_FUNCTION_REGEXP = re.compile(r"^([a-zA-Z0-9_]+)\(([0-9]+),([0-9]+|MAX)\)$")


def split_allowed_context(
    allowed_context: list[str],
) -> tuple[list[str], list[FunctionInfo]]:
    """Split a schema context list into named contexts and FunctionInfo objects.

    Each entry is either:
    - A plain context name (e.g. "github", "env.MY_VAR")
    - A function signature (e.g. "contains(2,2)", "hashFiles(1,MAX)")
    """
    named_contexts: list[str] = []
    functions: list[FunctionInfo] = []

    for item in allowed_context:
        match = _FUNCTION_REGEXP.match(item)
        if match:
            name = match.group(1)
            min_args = int(match.group(2))
            max_raw = match.group(3)
            max_args = (
                2**53 - 1  # JS Number.MAX_SAFE_INTEGER
                if max_raw == MAX_CONSTANT
                else int(max_raw)
            )
            functions.append(FunctionInfo(name=name, min_args=min_args, max_args=max_args))
        else:
            named_contexts.append(item)

    return named_contexts, functions
