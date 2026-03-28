"""IdBuilder — generates unique, valid identifiers for steps and jobs."""

from __future__ import annotations

_SEPARATOR = "_"
_MAX_ATTEMPTS = 1000
_MAX_LENGTH = 100


class IdBuilder:
    def __init__(self) -> None:
        self._name: list[str] = []
        self._distinct_names: set[str] = set()

    def append_segment(self, value: str) -> None:
        if not value:
            return

        if not self._name:
            first = value[0]
            if first.isalpha() or first == "_":
                pass  # legal first char
            elif first.isdigit() or first == "-":
                self._name.append("_")
            else:
                return  # illegal — skip
        else:
            self._name.append(_SEPARATOR)

        for c in value:
            if c.isalnum() or c in ("_", "-"):
                self._name.append(c)
            else:
                self._name.append(_SEPARATOR)

    def build(self) -> str:
        original = "".join(self._name) if self._name else "job"
        for attempt in range(1, _MAX_ATTEMPTS):
            suffix = "" if attempt == 1 else f"_{attempt}"
            candidate = (
                original[: min(len(original), _MAX_LENGTH - len(suffix))] + suffix
            )
            if candidate not in self._distinct_names:
                self._distinct_names.add(candidate)
                self._name = []
                return candidate
        raise RuntimeError("Unable to create a unique name")

    def try_add_known_id(self, value: str) -> str | None:
        """Add a known ID to the distinct set. Returns an error string if invalid."""
        if not value or not self._is_valid(value) or len(value) >= _MAX_LENGTH:
            return (
                f"The identifier '{value}' is invalid. IDs may only contain alphanumeric characters, "
                f"'_', and '-'. IDs must start with a letter or '_' and and must be less than "
                f"{_MAX_LENGTH} characters."
            )
        if value.startswith("__"):
            return f"The identifier '{value}' is invalid. IDs starting with '__' are reserved."
        if value in self._distinct_names:
            return f"The identifier '{value}' may not be used more than once within the same scope."
        self._distinct_names.add(value)
        return None

    def _is_valid(self, name: str) -> bool:
        for i, c in enumerate(name):
            if i == 0:
                if not (c.isalpha() or c == "_"):
                    return False
            elif not (c.isalnum() or c in ("_", "-")):
                return False
        return True
