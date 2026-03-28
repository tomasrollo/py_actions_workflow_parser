"""TemplateSchema — root schema object containing all type definitions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..templates.template_constants import (
    ALLOWED_VALUES,
    ANY,
    BOOLEAN,
    BOOLEAN_DEFINITION,
    BOOLEAN_DEFINITION_PROPERTIES,
    CONSTANT,
    CONTEXT,
    DEFINITION,
    DEFINITIONS,
    DESCRIPTION,
    IGNORE_CASE,
    IS_EXPRESSION,
    ITEM_TYPE,
    LOOSE_KEY_TYPE,
    LOOSE_VALUE_TYPE,
    MAPPING,
    MAPPING_DEFINITION,
    MAPPING_DEFINITION_PROPERTIES,
    MAPPING_PROPERTY_VALUE,
    NON_EMPTY_STRING,
    NULL,
    NULL_DEFINITION,
    NULL_DEFINITION_PROPERTIES,
    NUMBER,
    NUMBER_DEFINITION,
    NUMBER_DEFINITION_PROPERTIES,
    ONE_OF,
    ONE_OF_DEFINITION,
    PROPERTIES,
    PROPERTY_VALUE,
    REQUIRED,
    REQUIRE_NON_EMPTY,
    SCALAR,
    SEQUENCE,
    SEQUENCE_DEFINITION,
    SEQUENCE_DEFINITION_PROPERTIES,
    SEQUENCE_OF_NON_EMPTY_STRING,
    STRING,
    STRING_DEFINITION,
    STRING_DEFINITION_PROPERTIES,
    TEMPLATE_SCHEMA,
    TYPE,
    VERSION,
)
from ..tokens.types import TokenType
from .definition import Definition
from .definition_type import DefinitionType
from .mapping_definition import MappingDefinition
from .one_of_definition import OneOfDefinition
from .property_definition import PropertyDefinition
from .scalar_definition import ScalarDefinition
from .sequence_definition import SequenceDefinition
from .simple_definitions import BooleanDefinition, NullDefinition, NumberDefinition
from .string_definition import StringDefinition

if TYPE_CHECKING:
    from ..templates.object_reader import ObjectReader
    from .definition_info import DefinitionInfo


class TemplateSchema:
    """Models the root schema object and contains all type definitions."""

    _DEFINITION_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")
    _internal_schema: TemplateSchema | None = None

    def __init__(
        self, mapping: "MappingDefinition | None" = None
    ) -> None:  # noqa: F821 — actually MappingToken
        self.definitions: dict[str, Definition] = {}
        self.version: str = ""

        # Built-in type: null
        self.definitions[NULL] = NullDefinition(NULL)
        # Built-in type: boolean
        self.definitions[BOOLEAN] = BooleanDefinition(BOOLEAN)
        # Built-in type: number
        self.definitions[NUMBER] = NumberDefinition(NUMBER)
        # Built-in type: string
        self.definitions[STRING] = StringDefinition(STRING)
        # Built-in type: sequence
        sequence_definition = SequenceDefinition(SEQUENCE)
        sequence_definition.item_type = ANY
        self.definitions[sequence_definition.key] = sequence_definition
        # Built-in type: mapping
        mapping_definition = MappingDefinition(MAPPING)
        mapping_definition.loose_key_type = STRING
        mapping_definition.loose_value_type = ANY
        self.definitions[mapping_definition.key] = mapping_definition
        # Built-in type: any
        any_definition = OneOfDefinition(ANY)
        any_definition.one_of.extend([NULL, BOOLEAN, NUMBER, STRING, SEQUENCE, MAPPING])
        self.definitions[any_definition.key] = any_definition

        if mapping is not None:
            self._parse_mapping(mapping)

    # ------------------------------------------------------------------ #
    # Constructor helpers
    # ------------------------------------------------------------------ #

    def _parse_mapping(self, mapping: object) -> None:  # type: ignore[override]
        """Parse a MappingToken describing schema definitions."""
        # Import here to avoid circularity at module level
        from ..tokens.mapping_token import MappingToken
        from ..tokens.sequence_token import SequenceToken
        from ..tokens.string_token import StringToken

        assert isinstance(mapping, MappingToken)

        for pair in mapping:
            key = pair.key.assert_string(f"{TEMPLATE_SCHEMA} key")
            if key.value == VERSION:
                self.version = pair.value.assert_string(
                    f"{TEMPLATE_SCHEMA} {VERSION}"
                ).value
            elif key.value == DEFINITIONS:
                definitions_token = pair.value.assert_mapping(
                    f"{TEMPLATE_SCHEMA} {DEFINITIONS}"
                )
                for def_pair in definitions_token:
                    def_key = def_pair.key.assert_string(
                        f"{TEMPLATE_SCHEMA} {DEFINITIONS} key"
                    )
                    def_value = def_pair.value.assert_mapping(
                        f"{TEMPLATE_SCHEMA} {DEFINITIONS} value"
                    )
                    definition: Definition | None = None

                    for d_pair in def_value:
                        d_key = d_pair.key.assert_string(f"{DEFINITION} key")
                        if d_key.value == NULL:
                            definition = NullDefinition(def_key.value, def_value)
                        elif d_key.value == BOOLEAN:
                            definition = BooleanDefinition(def_key.value, def_value)
                        elif d_key.value == NUMBER:
                            definition = NumberDefinition(def_key.value, def_value)
                        elif d_key.value == STRING:
                            definition = StringDefinition(def_key.value, def_value)
                        elif d_key.value == SEQUENCE:
                            definition = SequenceDefinition(def_key.value, def_value)
                        elif d_key.value == MAPPING:
                            definition = MappingDefinition(def_key.value, def_value)
                        elif d_key.value == ONE_OF:
                            definition = OneOfDefinition(def_key.value, def_value)
                        elif d_key.value == ALLOWED_VALUES:
                            # Build a string definition for each allowed value item
                            for item_pair in def_value:
                                if (
                                    item_pair.value.template_token_type
                                    == TokenType.Sequence
                                ):
                                    sequence_token = item_pair.value
                                    assert isinstance(sequence_token, SequenceToken)
                                    for activity in sequence_token:
                                        if (
                                            activity.template_token_type
                                            == TokenType.String
                                        ):
                                            assert isinstance(activity, StringToken)
                                            av_key = (
                                                def_key.value + "-" + activity.value
                                            )
                                            av_def = StringDefinition(av_key)
                                            av_def.constant = (
                                                activity.to_display_string()
                                            )
                                            self.definitions[av_key] = av_def
                            definition = OneOfDefinition(def_key.value, def_value)
                        elif d_key.value in (CONTEXT, DESCRIPTION):
                            continue
                        else:
                            d_key.assert_unexpected_value(f"{DEFINITION} mapping key")
                        break

                    if definition is None:
                        raise ValueError(
                            f"Not enough information to construct definition '{def_key.value}'"
                        )
                    self.definitions[def_key.value] = definition
            else:
                key.assert_unexpected_value(f"{TEMPLATE_SCHEMA} key")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_definition(self, name: str) -> Definition:
        """Look up a definition by name; raises if not found."""
        result = self.definitions.get(name)
        if result is not None:
            return result
        raise KeyError(f"Schema definition '{name}' not found")

    def get_scalar_definitions(self, definition: Definition) -> list[ScalarDefinition]:
        """Expand one-of definitions and return all scalar definitions."""
        result: list[ScalarDefinition] = []
        dt = definition.definition_type
        if dt in (
            DefinitionType.Null,
            DefinitionType.Boolean,
            DefinitionType.Number,
            DefinitionType.String,
        ):
            result.append(definition)  # type: ignore[arg-type]
        elif dt == DefinitionType.OneOf:
            assert isinstance(definition, OneOfDefinition)
            for nested_name in definition.one_of:
                nested = self.get_definition(nested_name)
                result.extend(self.get_scalar_definitions(nested))
        return result

    def get_definitions_of_type(
        self, definition: Definition, type: DefinitionType
    ) -> list[Definition]:
        """Expand one-of definitions and return all matching definitions by type."""
        result: list[Definition] = []
        if definition.definition_type == type:
            result.append(definition)
        elif definition.definition_type == DefinitionType.OneOf:
            assert isinstance(definition, OneOfDefinition)
            for nested_name in definition.one_of:
                nested = self.get_definition(nested_name)
                if nested.definition_type == type:
                    result.append(nested)
        return result

    def match_property_and_filter(
        self, definitions: list[MappingDefinition], property_name: str
    ) -> PropertyDefinition | None:
        """Match a property name against multiple mapping definitions, filtering out non-matches."""
        result: PropertyDefinition | None = None
        not_found_in_some = False

        for definition in definitions:
            prop_def = definition.properties.get(property_name)
            if prop_def:
                result = prop_def
            else:
                not_found_in_some = True

        if result and not_found_in_some:
            i = 0
            while i < len(definitions):
                if definitions[i].properties.get(property_name):
                    i += 1
                else:
                    definitions.pop(i)

        return result

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate(self) -> None:
        one_of_definitions: dict[str, OneOfDefinition] = {}

        for name in list(self.definitions.keys()):
            if not self._DEFINITION_NAME_PATTERN.match(name):
                raise ValueError(f"Invalid definition name '{name}'")

            definition = self.definitions[name]
            if definition.definition_type == DefinitionType.OneOf:
                one_of_definitions[name] = definition  # type: ignore[assignment]
            else:
                definition.validate(self, name)

        # Validate one-of definitions after all others (they reference other defs)
        for name, one_of in one_of_definitions.items():
            one_of.validate(self, name)

    # ------------------------------------------------------------------ #
    # Static constructors
    # ------------------------------------------------------------------ #

    @staticmethod
    def load(object_reader: "ObjectReader") -> "TemplateSchema":
        """Load a user-defined schema from an object reader."""
        # These imports are deferred to avoid circular imports at module-load time.
        from ..templates.template_context import (
            TemplateContext,
            TemplateValidationErrors,
        )
        from ..templates.template_reader import read_template
        from ..templates.trace_writer import NoOperationTraceWriter

        context = TemplateContext(
            TemplateValidationErrors(10, 500),
            TemplateSchema.get_internal_schema(),
            NoOperationTraceWriter(),
        )
        template = read_template(context, TEMPLATE_SCHEMA, object_reader, None)
        context.errors.check()

        mapping = template.assert_mapping(TEMPLATE_SCHEMA)  # type: ignore[union-attr]
        schema = TemplateSchema(mapping)  # type: ignore[arg-type]
        schema._validate()
        return schema

    @staticmethod
    def get_internal_schema() -> "TemplateSchema":
        """Return (and cache) the built-in schema used to parse user schemas."""
        if TemplateSchema._internal_schema is not None:
            return TemplateSchema._internal_schema

        from ..tokens.string_token import StringToken

        schema = TemplateSchema()

        def _mp(key: str) -> MappingDefinition:
            md = MappingDefinition(key)
            schema.definitions[key] = md
            return md

        def _prop(type_name: str) -> PropertyDefinition:
            return PropertyDefinition(StringToken(None, None, type_name, None))

        # template-schema
        ts_map = _mp(TEMPLATE_SCHEMA)
        ts_map.properties[VERSION] = _prop(NON_EMPTY_STRING)
        ts_map.properties[DEFINITIONS] = _prop(DEFINITIONS)

        # definitions
        defs_map = _mp(DEFINITIONS)
        defs_map.loose_key_type = NON_EMPTY_STRING
        defs_map.loose_value_type = DEFINITION

        # definition (one-of of all definition types)
        def_oo = OneOfDefinition(DEFINITION)
        def_oo.one_of.extend(
            [
                NULL_DEFINITION,
                BOOLEAN_DEFINITION,
                NUMBER_DEFINITION,
                STRING_DEFINITION,
                SEQUENCE_DEFINITION,
                MAPPING_DEFINITION,
                ONE_OF_DEFINITION,
            ]
        )
        schema.definitions[DEFINITION] = def_oo

        # null-definition
        null_def_map = _mp(NULL_DEFINITION)
        null_def_map.properties[DESCRIPTION] = _prop(STRING)
        null_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        null_def_map.properties[NULL] = _prop(NULL_DEFINITION_PROPERTIES)
        # null-definition-properties
        _mp(NULL_DEFINITION_PROPERTIES)

        # boolean-definition
        bool_def_map = _mp(BOOLEAN_DEFINITION)
        bool_def_map.properties[DESCRIPTION] = _prop(STRING)
        bool_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        bool_def_map.properties[BOOLEAN] = _prop(BOOLEAN_DEFINITION_PROPERTIES)
        # boolean-definition-properties
        _mp(BOOLEAN_DEFINITION_PROPERTIES)

        # number-definition
        num_def_map = _mp(NUMBER_DEFINITION)
        num_def_map.properties[DESCRIPTION] = _prop(STRING)
        num_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        num_def_map.properties[NUMBER] = _prop(NUMBER_DEFINITION_PROPERTIES)
        # number-definition-properties
        _mp(NUMBER_DEFINITION_PROPERTIES)

        # string-definition
        str_def_map = _mp(STRING_DEFINITION)
        str_def_map.properties[DESCRIPTION] = _prop(STRING)
        str_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        str_def_map.properties[STRING] = _prop(STRING_DEFINITION_PROPERTIES)
        # string-definition-properties
        str_props_map = _mp(STRING_DEFINITION_PROPERTIES)
        str_props_map.properties[CONSTANT] = _prop(NON_EMPTY_STRING)
        str_props_map.properties[IGNORE_CASE] = _prop(BOOLEAN)
        str_props_map.properties[REQUIRE_NON_EMPTY] = _prop(BOOLEAN)
        str_props_map.properties[IS_EXPRESSION] = _prop(BOOLEAN)

        # sequence-definition
        seq_def_map = _mp(SEQUENCE_DEFINITION)
        seq_def_map.properties[DESCRIPTION] = _prop(STRING)
        seq_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        seq_def_map.properties[SEQUENCE] = _prop(SEQUENCE_DEFINITION_PROPERTIES)
        # sequence-definition-properties
        seq_props_map = _mp(SEQUENCE_DEFINITION_PROPERTIES)
        seq_props_map.properties[ITEM_TYPE] = _prop(NON_EMPTY_STRING)

        # mapping-definition
        map_def_map = _mp(MAPPING_DEFINITION)
        map_def_map.properties[DESCRIPTION] = _prop(STRING)
        map_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        map_def_map.properties[MAPPING] = _prop(MAPPING_DEFINITION_PROPERTIES)
        # mapping-definition-properties
        map_props_map = _mp(MAPPING_DEFINITION_PROPERTIES)
        map_props_map.properties[PROPERTIES] = _prop(PROPERTIES)
        map_props_map.properties[LOOSE_KEY_TYPE] = _prop(NON_EMPTY_STRING)
        map_props_map.properties[LOOSE_VALUE_TYPE] = _prop(NON_EMPTY_STRING)

        # properties
        props_map = _mp(PROPERTIES)
        props_map.loose_key_type = NON_EMPTY_STRING
        props_map.loose_value_type = PROPERTY_VALUE

        # property-value (one-of)
        prop_val_oo = OneOfDefinition(PROPERTY_VALUE)
        prop_val_oo.one_of.extend([NON_EMPTY_STRING, MAPPING_PROPERTY_VALUE])
        schema.definitions[PROPERTY_VALUE] = prop_val_oo

        # mapping-property-value
        map_prop_val_map = _mp(MAPPING_PROPERTY_VALUE)
        map_prop_val_map.properties[TYPE] = _prop(NON_EMPTY_STRING)
        map_prop_val_map.properties[REQUIRED] = _prop(BOOLEAN)
        map_prop_val_map.properties[DESCRIPTION] = _prop(STRING)

        # one-of-definition
        oo_def_map = _mp(ONE_OF_DEFINITION)
        oo_def_map.properties[DESCRIPTION] = _prop(STRING)
        oo_def_map.properties[CONTEXT] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        oo_def_map.properties[ONE_OF] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)
        oo_def_map.properties[ALLOWED_VALUES] = _prop(SEQUENCE_OF_NON_EMPTY_STRING)

        # non-empty-string
        non_empty_str = StringDefinition(NON_EMPTY_STRING)
        non_empty_str.require_non_empty = True
        schema.definitions[NON_EMPTY_STRING] = non_empty_str

        # sequence-of-non-empty-string
        seq_non_empty = SequenceDefinition(SEQUENCE_OF_NON_EMPTY_STRING)
        seq_non_empty.item_type = NON_EMPTY_STRING
        schema.definitions[SEQUENCE_OF_NON_EMPTY_STRING] = seq_non_empty

        schema._validate()
        TemplateSchema._internal_schema = schema
        return schema
