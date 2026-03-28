# Tasks — Python Reimplementation of GitHub Actions Workflow Parser

Each task builds on the previous ones. Validation criteria are included so progress can be verified after each task.

---

## Milestone 1: Parse a minimal workflow ✅

### Task 1: Template constants and token primitives ✅

Implement the foundational types that everything else depends on.

**Files to create:**
- `src/py_actions_workflow_parser/templates/template_constants.py` — all 47+ schema type-name constants (`STRING`, `BOOLEAN`, `MAPPING`, `OPEN_EXPRESSION`, `CLOSE_EXPRESSION`, etc.)
- `src/py_actions_workflow_parser/tokens/types.py` — `TokenType` enum and `token_type_name()` helper
- `src/py_actions_workflow_parser/tokens/token_range.py` — `Position` and `TokenRange` dataclasses

**Reference TS files:** `src/templates/template-constants.ts`, `src/templates/tokens/types.ts`, `src/templates/tokens/token-range.ts`

**Validation:** Import all three modules successfully; `TokenType` enum has 8 members; constants match the TS originals.

---

### Task 2: Token hierarchy — base classes and literal tokens ✅

Implement the `TemplateToken` base class, scalar tokens, and the key-value pair wrapper. Note: tokens reference `DefinitionInfo` from the schema module — use a forward reference or `TYPE_CHECKING` import for now and wire it up in Task 4.

**Files to create:**
- `src/py_actions_workflow_parser/tokens/template_token.py` — `TemplateToken` abstract base with `file`, `range`, `definition_info`, traversal iterator
- `src/py_actions_workflow_parser/tokens/scalar_token.py` — `ScalarToken` abstract base
- `src/py_actions_workflow_parser/tokens/literal_token.py` — `LiteralToken` abstract base
- `src/py_actions_workflow_parser/tokens/string_token.py` — `StringToken` (with block-scalar header support)
- `src/py_actions_workflow_parser/tokens/number_token.py` — `NumberToken`
- `src/py_actions_workflow_parser/tokens/boolean_token.py` — `BooleanToken`
- `src/py_actions_workflow_parser/tokens/null_token.py` — `NullToken`
- `src/py_actions_workflow_parser/tokens/key_value_pair.py` — `KeyValuePair`

**Reference TS files:** all files under `src/templates/tokens/` for the above types

**Validation:** Can construct each token type with a file ID, range, and value; `StringToken("hello")`, `NumberToken(42)`, `BooleanToken(True)`, `NullToken()` all instantiate without error.

---

### Task 3: Token hierarchy — composite and expression tokens ✅

Implement container tokens and expression tokens.

**Files to create:**
- `src/py_actions_workflow_parser/tokens/sequence_token.py` — `SequenceToken` (list of `TemplateToken`)
- `src/py_actions_workflow_parser/tokens/mapping_token.py` — `MappingToken` (list of `KeyValuePair`)
- `src/py_actions_workflow_parser/tokens/expression_token.py` — `ExpressionToken` abstract base with `validate_expression()` (calls `py_actions_expressions_parser.Lexer` + `Parser`)
- `src/py_actions_workflow_parser/tokens/basic_expression_token.py` — `BasicExpressionToken`
- `src/py_actions_workflow_parser/tokens/insert_expression_token.py` — `InsertExpressionToken`
- `src/py_actions_workflow_parser/tokens/type_guards.py` — `is_string()`, `is_number()`, `is_boolean()`, `is_mapping()`, `is_sequence()`, `is_basic_expression()`, etc.
- `src/py_actions_workflow_parser/tokens/__init__.py` — re-export all token types

**Reference TS files:** remaining files under `src/templates/tokens/`

**Validation:** Can build a mapping token containing string keys and sequence values; type guards return correct results; `ExpressionToken.validate_expression("github.ref", ["github"])` passes without error.

---

### Task 4: Schema definition hierarchy ✅

Implement the schema definition system used to drive validation.

**Files to create:**
- `src/py_actions_workflow_parser/schema/definition_type.py` — `DefinitionType` enum
- `src/py_actions_workflow_parser/schema/definition.py` — `Definition` base class with `reader_context`, `evaluator_context`, `key`, `description`
- `src/py_actions_workflow_parser/schema/scalar_definition.py` — `ScalarDefinition` base
- `src/py_actions_workflow_parser/schema/null_definition.py` — `NullDefinition`
- `src/py_actions_workflow_parser/schema/boolean_definition.py` — `BooleanDefinition`
- `src/py_actions_workflow_parser/schema/number_definition.py` — `NumberDefinition`
- `src/py_actions_workflow_parser/schema/string_definition.py` — `StringDefinition` (with constant/required/allowed-values support)
- `src/py_actions_workflow_parser/schema/sequence_definition.py` — `SequenceDefinition`
- `src/py_actions_workflow_parser/schema/mapping_definition.py` — `MappingDefinition` (properties + loose key/value types)
- `src/py_actions_workflow_parser/schema/one_of_definition.py` — `OneOfDefinition`
- `src/py_actions_workflow_parser/schema/property_definition.py` — `PropertyDefinition`
- `src/py_actions_workflow_parser/schema/definition_info.py` — `DefinitionInfo` wrapper with allowed-context accumulation
- `src/py_actions_workflow_parser/schema/__init__.py` — re-exports

**Reference TS files:** all files under `src/templates/schema/`

**Validation:** Can instantiate each definition type; `DefinitionInfo` correctly merges parent context with definition context; definition type enum has the expected members.

---

### Task 5: Schema loader (`TemplateSchema`) ✅

Implement the schema loader that reads the JSON schema files and builds a registry of definitions.

**Files to create:**
- `src/py_actions_workflow_parser/schema/template_schema.py` — `TemplateSchema` class with `load()`, `get_definition()`, `get_scalar_definitions()`, `get_definitions_of_type()`, `match_property_and_filter()`

**Files to copy:**
- `src/py_actions_workflow_parser/_schemas/workflow_v1_0.json` — from `original_code/workflow-parser/src/workflow-v1.0.json`
- `src/py_actions_workflow_parser/_schemas/action_v1_0.json` — from `original_code/workflow-parser/src/action-v1.0.json`

**Reference TS files:** `src/templates/schema/template-schema.ts`

**Validation:** `TemplateSchema.load(workflow_schema_json)` returns a schema; `schema.get_definition("workflow-root")` returns a `MappingDefinition`; the schema contains 500+ definitions.

---

### Task 6: Parse events + object reader protocol ✅

Implement the event stream abstraction that sits between YAML parsing and the template reader.

**Files to create:**
- `src/py_actions_workflow_parser/templates/parse_event.py` — `EventType` enum, `ParseEvent` dataclass
- `src/py_actions_workflow_parser/templates/object_reader.py` — `ObjectReader` protocol (`allow_literal()`, `allow_sequence_start()`, `allow_sequence_end()`, `allow_mapping_start()`, `allow_mapping_end()`, `validate_start()`, `validate_end()`)
- `src/py_actions_workflow_parser/templates/__init__.py`

**Reference TS files:** `src/templates/parse-event.ts`, `src/templates/object-reader.ts`

**Validation:** `EventType` enum has all event types; `ObjectReader` protocol can be used as a type annotation.

---

### Task 7: YAML object reader ✅

Implement the YAML→ParseEvent bridge using `ruamel.yaml`.

**Files to create:**
- `src/py_actions_workflow_parser/workflows/yaml_object_reader.py` — `YamlObjectReader` implementing `ObjectReader`
  - Recursive AST walker yielding `ParseEvent`s
  - Source position extraction (line/col)
  - YAML alias resolution with circular reference detection
  - Block scalar header preservation

**Reference TS files:** `src/workflows/yaml-object-reader.ts`

**Validation:** Parse `"on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi"` via `YamlObjectReader`; consuming events produces a `DocumentStart`, then literals/mapping/sequence events with correct values and line/col positions, then `DocumentEnd`.

---

### Task 8: JSON object reader ✅

Implement the JSON→ParseEvent reader (used internally by the schema loader to bootstrap parsing).

**Files to create:**
- `src/py_actions_workflow_parser/templates/json_object_reader.py` — `JsonObjectReader` implementing `ObjectReader`

**Reference TS files:** `src/templates/json-object-reader.ts`

**Validation:** Parse a small JSON object `{"key": "value", "list": [1, 2]}` and consume the correct event sequence.

---

### Task 9: Template context, errors, and trace writer ✅

Implement the parsing state holder and error accumulator.

**Files to create:**
- `src/py_actions_workflow_parser/templates/template_validation_error.py` — `TemplateValidationError` with message, file location, range
- `src/py_actions_workflow_parser/templates/trace_writer.py` — `TraceWriter` protocol + `NoOperationTraceWriter`
- `src/py_actions_workflow_parser/templates/template_context.py` — `TemplateContext` (schema, error collector, file ID registry, state dict) + `TemplateValidationErrors`
- `src/py_actions_workflow_parser/templates/template_parse_result.py` — `TemplateParseResult` container
- `src/py_actions_workflow_parser/templates/allowed_context.py` — `split_allowed_context()` that parses `"functionName(min,max)"` strings into named contexts and function info lists

**Reference TS files:** `src/templates/template-validation-error.ts`, `src/templates/trace-writer.ts`, `src/templates/template-context.ts`, `src/templates/template-parse-result.ts`, `src/templates/allowed-context.ts`

**Validation:** Create a `TemplateContext`; call `context.error(file_id, "test error")` and verify `context.errors.count == 1`; `split_allowed_context(["github", "contains(2,2)"])` returns the correct named contexts and function info list.

---

### Task 10: Template reader (core validator) ✅

Implement the schema-driven validation engine — the largest single module.

**Files to create:**
- `src/py_actions_workflow_parser/templates/template_reader.py` — `read_template()` function + `TemplateReader` class with:
  - `read_value()` — dispatch to scalar/sequence/mapping
  - `parse_scalar()` — detect and parse `${{ ... }}` expressions in strings
  - `handle_mapping_with_well_known_properties()` — schema property matching
  - `handle_mapping_with_all_loose_properties()` — dynamic key/value validation
  - `validate()` — scalar type checking and coercion
  - `parse_expression()` — expression extraction and validation
  - `skip_value()` — error recovery

**Key behaviors:** case-insensitive duplicate key detection; multi-expression string via synthetic `format()`; auto-coercion of non-string scalars; error accumulation without halting.

**Reference TS files:** `src/templates/template-reader.ts`

**Validation:** Using `YamlObjectReader` + `TemplateReader` with the workflow schema, parse a simple workflow YAML string and get back a `MappingToken` tree with correct structure. An invalid YAML key should produce a `TemplateValidationError` in context rather than an exception.

---

### Task 11: Workflow parser entry point ✅

Wire together YAML parsing, schema loading, and template reading into the `parse_workflow()` function.

**Files to create:**
- `src/py_actions_workflow_parser/workflows/file.py` — `File` dataclass (name + content)
- `src/py_actions_workflow_parser/workflows/workflow_schema.py` — loads `workflow_v1_0.json` as `TemplateSchema`
- `src/py_actions_workflow_parser/workflows/workflow_constants.py` — `WORKFLOW_ROOT` type constant
- `src/py_actions_workflow_parser/workflows/workflow_parser.py` — `parse_workflow(file, trace_or_context) -> TemplateParseResult`
- `src/py_actions_workflow_parser/workflows/__init__.py`

**Reference TS files:** `src/workflows/workflow-parser.ts`, `src/workflows/workflow-schema.ts`, `src/workflows/workflow-constants.ts`, `src/workflows/file.ts`

**Validation — Milestone 1 checkpoint:**
```python
from py_actions_workflow_parser.workflows.file import File
from py_actions_workflow_parser.workflows.workflow_parser import parse_workflow
from py_actions_workflow_parser.templates.trace_writer import NoOperationTraceWriter

f = File(name="test.yml", content="on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi")
result = parse_workflow(f, NoOperationTraceWriter())
assert result.value is not None
assert result.context.errors.count == 0
```

---

## Milestone 2: Expression validation works ✅

### Task 12: Expression validation in template reader ✅

Ensure `${{ ... }}` expressions embedded in YAML values are validated against allowed context using `py-actions-expressions-parser`.

This should already be partially wired from Tasks 3 and 10. This task is about end-to-end verification and fixing any integration issues.

**Verify/fix:**
- `ExpressionToken.validate_expression()` correctly calls `Lexer` + `Parser` from `py_actions_expressions_parser`
- `allowed_context.py` produces correct `named_contexts` and `functions` lists from schema context arrays
- `template_reader.py` correctly passes allowed context through `DefinitionInfo` during expression parsing
- Invalid expressions produce `TemplateValidationError` entries in context

**Validation — Milestone 2 checkpoint:**
```python
# Valid expression passes
f = File(name="test.yml", content="on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    if: ${{ github.ref == 'refs/heads/main' }}\n    steps:\n      - run: echo hi")
result = parse_workflow(f, NoOperationTraceWriter())
assert result.context.errors.count == 0

# Invalid expression produces error
f2 = File(name="bad.yml", content="on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    if: ${{ github.event = 12 }}\n    steps:\n      - run: echo hi")
result2 = parse_workflow(f2, NoOperationTraceWriter())
assert result2.context.errors.count >= 1
```

---

## Milestone 3: Full conversion pipeline ✅

### Task 13: Workflow data model ✅

Implement the typed data model dataclasses that conversion produces.

**Files to create:**
- `src/py_actions_workflow_parser/model/workflow_template.py` — all dataclasses:
  - `WorkflowTemplate`, `EventsConfig`
  - `Job`, `ReusableWorkflowJob` (discriminated by `type` field)
  - `RunStep`, `ActionStep` (discriminated by type)
  - `Container`, `ConcurrencySetting`, `EnvironmentRef`
  - Event types: `ScheduleConfig`, `WorkflowDispatchConfig`, `WorkflowCallConfig`, push/PR filter configs
  - Input/output/secret definition types
- `src/py_actions_workflow_parser/model/type_guards.py` — `is_run_step()`, `is_action_step()`, `is_job()`, `is_reusable_workflow_job()`
- `src/py_actions_workflow_parser/model/__init__.py`

**Reference TS files:** `src/model/workflow-template.ts`, `src/model/type-guards.ts`

**Validation:** Can instantiate `WorkflowTemplate(jobs=[...], errors=[])` and all nested types; type guards return correct results.

---

### Task 14: File reference parsing ✅

Implement the utility for parsing reusable workflow references.

**Files to create:**
- `src/py_actions_workflow_parser/workflows/file_reference.py` — `LocalFileReference`, `RemoteFileReference`, `parse_file_reference()`
- `src/py_actions_workflow_parser/workflows/file_provider.py` — `FileProvider` protocol

**Reference TS files:** `src/workflows/file-reference.ts`, `src/workflows/file-provider.ts`

**Validation:** `parse_file_reference("./local/path")` returns `LocalFileReference`; `parse_file_reference("owner/repo/path@v1")` returns `RemoteFileReference` with correct `owner`, `repository`, `path`, `version`.

---

### Task 15: Converter utilities ✅

Implement the small shared converter helpers that the main converters depend on.

**Files to create:**
- `src/py_actions_workflow_parser/model/converter/__init__.py`
- `src/py_actions_workflow_parser/model/converter/handle_errors.py` — `handle_template_token_errors()` wrapper
- `src/py_actions_workflow_parser/model/converter/string_list.py` — sequence → string array conversion
- `src/py_actions_workflow_parser/model/converter/id_builder.py` — `IdBuilder` for unique step/job ID generation with conflict resolution
- `src/py_actions_workflow_parser/model/converter/cron.py` — cron expression validation
- `src/py_actions_workflow_parser/model/converter/concurrency.py` — `convert_concurrency()`
- `src/py_actions_workflow_parser/model/converter/container.py` — `convert_to_job_container()`

**Reference TS files:** corresponding files under `src/model/converter/`

**Validation:** `IdBuilder` generates `__run`, `__run1`, `__run2` for three unnamed run steps; cron validation rejects `* * * * *` (every minute); `convert_concurrency()` handles both string shorthand and mapping forms.

---

### Task 16: If-condition converter (AST walking) ✅

Implement the converter that wraps `if` conditions with `success() &&` when no status function is present. This walks the `py_actions_expressions_parser` AST.

**Files to create:**
- `src/py_actions_workflow_parser/model/converter/if_condition.py` — `convert_to_if_condition()`, `ensure_status_function()`, `walk_tree_to_find_status_function_calls()`

**Reference TS files:** `src/model/converter/if-condition.ts`

**Validation:** `ensure_status_function("github.ref == 'main'")` returns `"success() && (github.ref == 'main')"`. `ensure_status_function("failure()")` returns `"failure()"` unchanged.

---

### Task 17: Event, job, and step converters ✅

Implement the main converters that transform the token tree into the data model.

**Files to create:**
- `src/py_actions_workflow_parser/model/converter/events.py` — `convert_on()` handling string/sequence/mapping event forms, schedule, workflow_dispatch, workflow_call, pattern filters
- `src/py_actions_workflow_parser/model/converter/jobs.py` — `convert_jobs()` with dependency cycle detection (BFS)
- `src/py_actions_workflow_parser/model/converter/job.py` — `convert_job()` extracting all job properties
- `src/py_actions_workflow_parser/model/converter/steps.py` — `convert_steps()` with auto-ID generation
- `src/py_actions_workflow_parser/model/converter/runs_on.py` — `convert_runs_on()`
- `src/py_actions_workflow_parser/model/converter/environment.py` — `convert_to_actions_environment_ref()`
- `src/py_actions_workflow_parser/model/converter/workflow_dispatch.py` — `convert_event_workflow_dispatch_inputs()`
- `src/py_actions_workflow_parser/model/converter/workflow_call.py` — `convert_event_workflow_call()`
- `src/py_actions_workflow_parser/model/converter/inputs.py` — reusable workflow input conversion
- `src/py_actions_workflow_parser/model/converter/secrets.py` — secret conversion

**Reference TS files:** corresponding files under `src/model/converter/` and `src/model/converter/job/`

**Validation:** Parse and convert a workflow with two jobs where `job_b` needs `job_a`; verify the dependency is captured. Parse a workflow with circular `needs` and verify an error is produced.

---

### Task 18: Main `convert_workflow_template()` + referenced workflows ✅

Implement the top-level conversion entry point.

**Files to create:**
- `src/py_actions_workflow_parser/model/converter/convert.py` — `convert_workflow_template(context, root, file_provider, options)`
- `src/py_actions_workflow_parser/model/converter/referenced_workflow.py` — `convert_referenced_workflow()`

**Reference TS files:** `src/model/convert.ts`, `src/model/converter/referencedWorkflow.ts`

**Validation — Milestone 3 checkpoint:**
```python
f = File(name="test.yml", content="""
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: echo hi
""")
result = parse_workflow(f, NoOperationTraceWriter())
wt = convert_workflow_template(result.context, result.value)
assert len(wt.jobs) == 1
assert wt.jobs[0].id == "build"
assert len(wt.jobs[0].steps) == 2
```

---

## Milestone 4: Test suite passes ✅

### Task 19: Public API exports ✅

Wire up the public `__init__.py` so the library is usable.

**Files to create/update:**
- `src/py_actions_workflow_parser/__init__.py` — export `parse_workflow`, `convert_workflow_template`, `WorkflowTemplate`, `TemplateParseResult`, `TraceWriter`, `NoOperationTraceWriter`, token type guards

**Reference TS files:** `src/index.ts`

**Validation:** `from py_actions_workflow_parser import parse_workflow, convert_workflow_template` works.

---

### Task 20: Test harness for fixture files ✅

Build a pytest-based test runner that loads the 196 YAML test fixtures and compares output against expected JSON.

**Files to create:**
- `tests/conftest.py` — fixture file loader, test YAML splitter, skipped-tests loader
- `tests/test_workflow_fixtures.py` — parametrized test that for each fixture file: parses workflow, converts to template, serializes to JSON, compares against expected JSON string

The test file format is: 3+ YAML documents separated by `---`, where doc[0] is test options, doc[1] is the workflow YAML, doc[-1] is expected JSON. For reusable workflows, intermediate docs provide additional file name/content pairs.

**Test data:** symlink or copy `original_code/workflow-parser/testdata/reader/` to `tests/testdata/reader/`. Load `testdata/skipped-tests.txt` and mark those tests as `pytest.mark.xfail`.

**Validation:** Test runner discovers all 196 fixture files; non-skipped tests are collected; at least 1 simple test (like `basic.yml`) passes end-to-end.

---

### Task 21: JSON serialization of workflow template ✅

Implement the serialization that converts a `WorkflowTemplate` into the exact JSON format the test fixtures expect. The format uses type codes (`type: 1` for sequence, `type: 2` for mapping, `type: 3` for expression) and specific field names.

**Reference:** Study the expected JSON in `testdata/reader/basic.yml` and `testdata/reader/mvp.yml` for the exact format.

**Validation:** Serializing the result of a simple workflow produces JSON that matches `basic.yml` expected output.

---

### Task 22: Fix failures and pass the test suite ✅

Iterate on the implementation to fix test failures discovered by the fixture test harness. Common issues will be:
- JSON serialization format mismatches
- Edge cases in the template reader (expression parsing, mapping handling)
- Missing or incorrect converter logic
- Error message formatting differences

**Validation — Milestone 4 checkpoint:** All non-skipped fixture tests pass. Skipped tests are marked `xfail`.

---

## Milestone 5: Action parsing ⏳

### Task 23: Action parser and action template ⏳

Implement the action manifest parser and converter.

**Files to create:**
- `src/py_actions_workflow_parser/actions/__init__.py`
- `src/py_actions_workflow_parser/actions/action_constants.py` — `ACTION_ROOT` type constant
- `src/py_actions_workflow_parser/actions/action_schema.py` — loads `action_v1_0.json` as `TemplateSchema`
- `src/py_actions_workflow_parser/actions/action_parser.py` — `parse_action(file, trace_or_context) -> TemplateParseResult`
- `src/py_actions_workflow_parser/actions/action_template.py` — `ActionTemplate` dataclass + `convert_action_template()`
  - `ActionInputDefinition`, `ActionOutputDefinition`
  - `ActionRunsComposite`, `ActionRunsNode`, `ActionRunsDocker`

**Reference TS files:** all files under `src/actions/`

**Validation — Milestone 5 checkpoint:**
```python
f = File(name="action.yml", content="""
name: 'My Action'
description: 'A test action'
inputs:
  who-to-greet:
    description: 'Who to greet'
    required: true
    default: 'World'
runs:
  using: 'node20'
  main: 'index.js'
""")
result = parse_action(f, NoOperationTraceWriter())
assert result.value is not None
assert result.context.errors.count == 0
```

---

### Task 24: Update public API with action exports ⏳

Add action-related exports to the public `__init__.py`.

**Files to update:**
- `src/py_actions_workflow_parser/__init__.py` — add `parse_action`, `ActionTemplate`

**Validation:** `from py_actions_workflow_parser import parse_action` works.
