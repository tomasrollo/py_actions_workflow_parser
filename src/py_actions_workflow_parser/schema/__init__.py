"""Schema definition hierarchy for template validation."""

from __future__ import annotations

from .definition import Definition
from .definition_info import DefinitionInfo
from .definition_type import DefinitionType
from .mapping_definition import MappingDefinition
from .one_of_definition import OneOfDefinition
from .property_definition import PropertyDefinition
from .scalar_definition import ScalarDefinition
from .sequence_definition import SequenceDefinition
from .simple_definitions import BooleanDefinition, NullDefinition, NumberDefinition
from .string_definition import StringDefinition
from .template_schema import TemplateSchema

__all__ = [
    "Definition",
    "DefinitionInfo",
    "DefinitionType",
    "MappingDefinition",
    "OneOfDefinition",
    "PropertyDefinition",
    "ScalarDefinition",
    "SequenceDefinition",
    "BooleanDefinition",
    "NullDefinition",
    "NumberDefinition",
    "StringDefinition",
    "TemplateSchema",
]
