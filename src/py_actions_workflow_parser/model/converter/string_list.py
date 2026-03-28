"""convert_string_list — sequence token → list[str] converter."""

from __future__ import annotations

from ...tokens.sequence_token import SequenceToken


def convert_string_list(name: str, token: SequenceToken) -> list[str]:
    result: list[str] = []
    for item in token:
        result.append(item.assert_string(f"{name} item").value)
    return result
