"""TemplateContext and TemplateValidationErrors — context flowed through parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .template_validation_error import TemplateValidationError
from .trace_writer import TraceWriter

if TYPE_CHECKING:
    from ..schema.template_schema import TemplateSchema
    from ..tokens.template_token import TemplateToken
    from ..tokens.token_range import TokenRange


class TemplateValidationErrors:
    """Collects validation errors during template parsing/evaluation."""

    def __init__(self, max_errors: int = 0, max_message_length: int = 0) -> None:
        self._max_errors = max_errors
        self._max_message_length = max_message_length
        self._errors: list[TemplateValidationError] = []

    @property
    def count(self) -> int:
        return len(self._errors)

    def add(self, err: TemplateValidationError | list[TemplateValidationError]) -> None:
        errors = err if isinstance(err, list) else [err]
        for e in errors:
            if self._max_errors <= 0 or len(self._errors) < self._max_errors:
                if (
                    self._max_message_length > 0
                    and len(e.message) > self._max_message_length
                ):
                    e = TemplateValidationError(
                        e.raw_message[: self._max_message_length] + "[...]",
                        e.prefix,
                        e.code,
                        e.range,
                    )
                self._errors.append(e)

    def check(self, prefix: str = "") -> None:
        """Raise if any errors have been collected."""
        if not self._errors:
            return
        if not prefix:
            prefix = "The template is not valid."
        raise ValueError(f"{prefix} {', '.join(e.message for e in self._errors)}")

    def clear(self) -> None:
        self._errors.clear()

    def get_errors(self) -> list[TemplateValidationError]:
        return list(self._errors)


class TemplateContext:
    """Context object flowed through template loading and evaluation."""

    def __init__(
        self,
        errors: TemplateValidationErrors,
        schema: "TemplateSchema",
        trace: TraceWriter,
    ) -> None:
        self.errors = errors
        self.schema = schema
        self.trace = trace
        self.state: dict[str, Any] = {}

        self._file_ids: dict[str, int] = {}
        self._file_names: list[str] = []

        # Available expression contexts
        from py_actions_expressions_parser import FunctionInfo  # type: ignore[import]

        self.expression_functions: list[FunctionInfo] = []
        self.expression_named_contexts: list[str] = []

    def error(
        self,
        token_or_file_id: "TemplateToken | int | None",
        err: "str | Exception",
        token_range: "TokenRange | None" = None,
    ) -> None:
        token = (
            token_or_file_id
            if not isinstance(token_or_file_id, (int, type(None)))
            else None
        )
        range_ = token_range or (token.range if token is not None else None)
        file_id = token.file if token is not None else (token_or_file_id if isinstance(token_or_file_id, int) else None)  # type: ignore[union-attr]
        line = getattr(token, "line", None) if token is not None else None
        col = getattr(token, "col", None) if token is not None else None
        prefix = self._get_error_prefix(file_id, line, col)
        message = err.args[0] if isinstance(err, Exception) and err.args else str(err)
        e = TemplateValidationError(message, prefix or None, None, range_)
        self.errors.add(e)
        self.trace.error(e.message)

    def get_file_id(self, file: str) -> int:
        key = file.upper()
        if key not in self._file_ids:
            self._file_ids[key] = len(self._file_names) + 1
            self._file_names.append(file)
        return self._file_ids[key]

    def get_file_name(self, file_id: int) -> str | None:
        return (
            self._file_names[file_id - 1] if len(self._file_names) >= file_id else None
        )

    def get_file_table(self) -> list[str]:
        return list(self._file_names)

    def _get_error_prefix(
        self,
        file_id: int | None,
        line: int | None,
        column: int | None,
    ) -> str:
        file_name = self.get_file_name(file_id) if file_id is not None else None
        if file_name:
            if line is not None and column is not None:
                return f"{file_name} (Line: {line}, Col: {column})"
            return file_name
        if line is not None and column is not None:
            return f"(Line: {line}, Col: {column})"
        return ""
