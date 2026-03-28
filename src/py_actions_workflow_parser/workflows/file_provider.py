"""FileProvider protocol for loading workflow files."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .file import File
    from .file_reference import FileReference


class FileProvider(ABC):
    @abstractmethod
    def get_file_content(self, ref: "FileReference") -> "File": ...
