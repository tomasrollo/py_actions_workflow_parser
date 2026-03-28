"""DefinitionType enum for schema definition types."""

from enum import IntEnum


class DefinitionType(IntEnum):
    Null = 0
    Boolean = 1
    Number = 2
    String = 3
    Sequence = 4
    Mapping = 5
    OneOf = 6
    AllowedValues = 7
