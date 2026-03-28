"""TraceWriter protocol and no-op implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TraceWriter(ABC):
    @abstractmethod
    def error(self, message: str) -> None: ...

    @abstractmethod
    def info(self, message: str) -> None: ...

    @abstractmethod
    def verbose(self, message: str) -> None: ...


class NoOperationTraceWriter(TraceWriter):
    def error(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def verbose(self, message: str) -> None:
        pass
