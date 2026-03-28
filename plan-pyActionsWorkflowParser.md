# Python Reimplementation Plan: GitHub Actions Workflow Parser

## 1. Overview

The TypeScript library (`@actions/workflow-parser` v0.3.49) is a **schema-driven YAML parser and validator** for GitHub Actions workflow files (`workflow.yml`) and action manifests (`action.yml`). It parses YAML into a validated token tree, then converts that tree into typed data models.

**Estimated scope:** ~10,500 lines of TypeScript across ~79 source files → approximately 5,500–6,500 lines of Python (Python is typically more concise, and the expression parser is available as an existing library).

### Architecture Summary

```
YAML string
    ↓
YamlObjectReader (YAML → stream of ParseEvents)
    ↓
TemplateReader (schema-driven validation → TemplateToken AST)
    ↓
Converter (TemplateToken AST → WorkflowTemplate / ActionTemplate)
    ↓
Typed data models (jobs, steps, events, etc.)
```

### Public API Surface (TypeScript)

```python
# What we need to expose in Python:
parse_workflow(file, trace) -> TemplateParseResult   # Main entry point
convert_workflow_template(context, root, ...) -> WorkflowTemplate  # Token → model
parse_action(file, trace) -> TemplateParseResult     # Action manifest parser

# Supporting types:
WorkflowTemplate, ActionTemplate                     # Output models
TemplateToken (and subtypes)                         # AST nodes
TemplateContext, TemplateValidationError              # Error handling
TraceWriter                                          # Logging interface
```

---

## 2. Key Design Decisions

### 2.1 Python Version & Tooling

- **Python ≥ 3.13** (already configured in `pyproject.toml`)
- **Build tool:** uv (already configured)
- **Testing:** pytest (already in dev dependencies)
- **Type hints:** Use `dataclasses` and `typing` extensively — the TS code is heavily typed

### 2.2 Dependencies

| TypeScript Dependency | Python Equivalent | Notes |
|---|---|---|
| `yaml` (v2.0+) | `ruamel.yaml` | Preserves source positions (line/col), round-trip parsing, YAML 1.1/1.2 support. PyYAML does **not** preserve positions well enough. |
| `@actions/expressions` | `py-actions-expressions-parser` | Full Python port of the TS library. Provides `Lexer`, `Parser`, AST nodes, and `Evaluator`. Already added to the project. |
| `cronstrue` | `croniter` or custom | For cron validation. `croniter` validates; `cronstrue` only describes. We need validation. |

### 2.3 Package Structure

```
src/py_actions_workflow_parser/
├── __init__.py                      # Public API exports
├── _schemas/
│   ├── workflow_v1_0.json           # Copied from original
│   └── action_v1_0.json            # Copied from original
├── tokens/
│   ├── __init__.py
│   ├── template_token.py           # Base + ScalarToken, LiteralToken
│   ├── string_token.py
│   ├── number_token.py
│   ├── boolean_token.py
│   ├── null_token.py
│   ├── sequence_token.py
│   ├── mapping_token.py
│   ├── expression_token.py         # BasicExpressionToken, InsertExpressionToken
│   ├── key_value_pair.py
│   └── type_guards.py
├── schema/
│   ├── __init__.py
│   ├── template_schema.py          # Schema loader + definition registry
│   ├── definition.py               # Base Definition + DefinitionInfo
│   ├── definition_types.py         # All concrete definition classes
│   └── property_definition.py
├── templates/
│   ├── __init__.py
│   ├── template_reader.py          # Core parser + validator (~850 LOC in TS)
│   ├── template_context.py         # Error accumulator + state
│   ├── template_constants.py       # Schema type name constants
│   ├── allowed_context.py          # Function signature parsing
│   ├── object_reader.py            # Protocol/ABC for object readers
│   ├── json_object_reader.py
│   ├── parse_event.py
│   ├── template_validation_error.py
│   └── trace_writer.py
├── workflows/
│   ├── __init__.py
│   ├── workflow_parser.py          # parseWorkflow entry point
│   ├── workflow_schema.py          # Schema loader for workflows
│   ├── workflow_constants.py
│   ├── yaml_object_reader.py       # YAML → ParseEvent stream
│   ├── file.py                     # File interface
│   ├── file_provider.py            # Protocol for fetching referenced files
│   └── file_reference.py           # Local/Remote file ref parsing
├── actions/
│   ├── __init__.py
│   ├── action_parser.py
│   ├── action_schema.py
│   ├── action_constants.py
│   └── action_template.py
└── model/
    ├── __init__.py
    ├── workflow_template.py         # WorkflowTemplate dataclass
    ├── type_guards.py
    └── converter/
        ├── __init__.py
        ├── convert.py               # Main convertWorkflowTemplate
        ├── events.py
        ├── jobs.py
        ├── job.py
        ├── steps.py
        ├── if_condition.py
        ├── concurrency.py
        ├── container.py
        ├── cron.py
        ├── id_builder.py
        ├── string_list.py
        ├── runs_on.py
        ├── environment.py
        ├── inputs.py
        ├── secrets.py
        ├── workflow_call.py
        ├── workflow_dispatch.py
        ├── referenced_workflow.py
        └── handle_errors.py
```

### 2.4 Idiom Mapping (TypeScript → Python)

| TypeScript | Python |
|---|---|
| `interface` / `type` | `dataclass` or `TypedDict` |
| `class` with readonly props | `@dataclass(frozen=True)` or `@dataclass` |
| `abstract class` | `ABC` + `@abstractmethod` |
| `enum` | `enum.Enum` or `enum.IntEnum` |
| Union types `A \| B` | `A \| B` (Python 3.10+) |
| Type guards `x is Foo` | `isinstance()` checks, or `TypeGuard` |
| `Generator<T>` / `yield` | `Generator[T, None, None]` / `yield` |
| `Promise<T>` / `async` | Not needed initially (see §2.5) |
| `implements Interface` | `Protocol` from `typing` |

### 2.5 Sync vs Async

The TS code is async only for `convertWorkflowTemplate` (fetching referenced workflows via `fileProvider`). The Python version should:

- Make the core parsing **synchronous** (no async needed for `parse_workflow`, `parse_action`)
- Offer `FileProvider` as a `Protocol` with a sync method initially
- Add an async variant later if needed

---

## 3. Implementation Phases

### Phase 1: Foundation — Tokens, Schema, and Constants

**Goal:** Build the core type system that everything else depends on.

**Modules:**
1. `tokens/` — All token classes (`TemplateToken` hierarchy)
   - Base class with `file_id`, `range`, `definition_info` tracking
   - All 8 concrete types: String, Number, Boolean, Null, Sequence, Mapping, BasicExpression, InsertExpression
   - `KeyValuePair` wrapper for mapping entries
   - Iterator support for tree traversal
   - Type guard functions

2. `schema/` — Definition hierarchy + schema loader
   - `Definition` base with `DefinitionType` enum
   - Concrete definitions: Null, Boolean, Number, String, Sequence, Mapping, OneOf
   - `PropertyDefinition` for mapping properties
   - `DefinitionInfo` wrapper with context accumulation
   - `TemplateSchema` — loads JSON schema files, builds definition registry

3. `templates/template_constants.py` — All 47+ schema type name constants

4. `_schemas/` — Copy the JSON schema files from the original code

**Estimated effort:** ~1,500 lines Python

### Phase 2: YAML Parsing + Object Reader

**Goal:** Parse YAML files into a stream of `ParseEvent`s consumable by the template reader.

**Modules:**
1. `templates/parse_event.py` — Event types (DocumentStart/End, Literal, SequenceStart/End, MappingStart/End)
2. `templates/object_reader.py` — `ObjectReader` protocol
3. `workflows/yaml_object_reader.py` — `YamlObjectReader` using `ruamel.yaml`
   - Recursive AST walker yielding ParseEvents
   - Source position extraction (line/col from ruamel.yaml)
   - YAML alias resolution with circular reference detection
   - Block scalar header preservation
4. `templates/json_object_reader.py` — JSON variant (used for schema loading)

**Key consideration:** `ruamel.yaml` provides `lc` (line/column) attributes on parsed nodes, which maps well to the TypeScript `yaml` library's `LineCounter`. Test round-trip position accuracy early.

**Estimated effort:** ~500 lines Python

### Phase 3: Expression Language Integration

**Goal:** Integrate the existing `py-actions-expressions-parser` library.

The `py-actions-expressions-parser` package is a full Python port of the TypeScript `@actions/expressions` library, sharing the same test suite for cross-language correctness. It is already added to the project as a dependency.

**API mapping (TypeScript → Python):**

| TypeScript (`@actions/expressions`) | Python (`py_actions_expressions_parser`) |
|---|---|
| `new Lexer(expr).lex()` | `Lexer(expr).lex()` |
| `new Parser(tokens, namedContexts, functions).parse()` | `Parser(tokens, context_names, []).parse()` |
| `FunctionInfo` | Pass dicts or `FunctionInfo`-compatible objects |
| `ExpressionError` (parse/lex) | `ExpressionError` with `.pos.column` |
| AST nodes: `FunctionCall`, `Binary`, etc. | Available in `py_actions_expressions_parser.ast` |

**Integration points in the workflow parser:**
1. `expression_token.py` — `validate_expression()` calls `Lexer` + `Parser` to validate `${{ }}` contents
2. `allowed_context.py` — parses `"functionName(min,max)"` strings into context names and function info, then passes them to the `Parser`
3. `if_condition.py` — walks the parsed AST to detect status function calls (`success()`, `failure()`, `cancelled()`, `always()`)

**Usage example:**
```python
from py_actions_expressions_parser import Lexer, Parser, ExpressionError

def validate_expression(expression: str, allowed_context: list[str]) -> None:
    named_contexts, functions = split_allowed_context(allowed_context)
    tokens = Lexer(expression).lex()
    Parser(tokens, named_contexts, functions).parse()  # raises ExpressionError on invalid
```

**No custom code needed** — this phase is purely about wiring the existing library into the template reader and converter modules.

**Estimated effort:** ~50 lines Python (adapter/glue code only)

### Phase 4: Template Reader (Core Validator)

**Goal:** Implement the schema-driven validation engine that converts ParseEvents into a validated TemplateToken tree.

This is the **largest and most complex module** (~850 lines in TS).

**Modules:**
1. `templates/template_reader.py`
   - `read_template(context, type, object_reader, file_id)` — main entry
   - `TemplateReader` class with methods:
     - `read_value()` — dispatch to scalar/sequence/mapping
     - `parse_scalar()` — detect and parse `${{ ... }}` expressions in strings
     - `handle_mapping_with_well_known_properties()` — schema property matching
     - `handle_mapping_with_all_loose_properties()` — dynamic key/value validation
     - `validate()` — scalar type checking and coercion
     - `parse_expression()` — expression extraction and validation
     - `skip_value()` — error recovery

2. `templates/template_context.py`
   - `TemplateContext` — parsing state holder
   - `TemplateValidationErrors` — error accumulator with limits

3. `templates/template_validation_error.py` — structured error with location
4. `templates/trace_writer.py` — `TraceWriter` protocol + `NoOperationTraceWriter`
5. `templates/allowed_context.py` — parse `"functionName(min,max)"` strings
6. `templates/template_parse_result.py` — result container

**Key behaviors to preserve:**
- Case-insensitive duplicate key detection in mappings
- Expression parsing: find all `${{ ... }}` sequences, handle nested quotes
- Multi-expression string concatenation via synthetic `format()` calls
- Auto-coercion of non-string scalars to strings when schema allows
- Error recovery: continue parsing after errors, accumulate all errors
- Ambiguous definition disambiguation reporting

**Estimated effort:** ~1,500 lines Python

### Phase 5: Workflow & Action Parsers

**Goal:** Thin entry points that wire together YAML parsing, schema loading, and template reading.

**Modules:**
1. `workflows/workflow_parser.py` — `parse_workflow(file, trace_or_context)`
2. `workflows/workflow_schema.py` — loads workflow-v1.0.json
3. `workflows/workflow_constants.py` — `WORKFLOW_ROOT` constant
4. `workflows/file.py` — `File` dataclass (name + content)
5. `workflows/file_reference.py` — `parse_file_reference()` → Local or Remote ref
6. `workflows/file_provider.py` — `FileProvider` protocol
7. `actions/action_parser.py` — `parse_action(file, trace_or_context)`
8. `actions/action_schema.py` — loads action-v1.0.json
9. `actions/action_constants.py` — `ACTION_ROOT` constant

**Estimated effort:** ~300 lines Python

### Phase 6: Model Conversion

**Goal:** Convert validated TemplateToken trees into typed `WorkflowTemplate` and `ActionTemplate` data models.

**Modules:**
1. `model/workflow_template.py` — All dataclasses:
   - `WorkflowTemplate`, `EventsConfig`, `ScheduleConfig`
   - `Job`, `ReusableWorkflowJob` (discriminated union)
   - `RunStep`, `ActionStep` (discriminated union)
   - `Container`, `ConcurrencySetting`, `EnvironmentRef`
   - Event filter types (push, PR, workflow_dispatch, workflow_call, etc.)
2. `model/type_guards.py` — `is_run_step()`, `is_action_step()`, etc.
3. `model/converter/convert.py` — Main `convert_workflow_template()`
4. `model/converter/events.py` — Event trigger conversion
5. `model/converter/jobs.py` — Job list + dependency cycle detection (BFS)
6. `model/converter/job.py` — Single job property extraction
7. `model/converter/steps.py` — Step conversion + auto-ID generation
8. `model/converter/if_condition.py` — `success() &&` wrapping via AST walking
9. `model/converter/*.py` — ~10 more small converter modules

10. `actions/action_template.py` — `ActionTemplate` + `convert_action_template()`

**Estimated effort:** ~2,000 lines Python

### Phase 7: Testing

**Goal:** Port the test infrastructure and validate against the 196 test fixtures.

**Strategy:**
1. **Reuse the 196 YAML test fixtures** — they contain input + expected output in a single file
2. Build a **test harness** that:
   - Reads each `.yml` test file
   - Splits on `---` separator into: directives, input YAML, expected JSON
   - Parses directives (e.g., `include-source: false`)
   - Runs `parse_workflow()` + `convert_workflow_template()` on input
   - Compares output JSON against expected
3. Start with the ~100 non-skipped test files
4. Mark the 48 skipped tests (from `skipped-tests.txt`) as `pytest.mark.skip`

**Test organization:**
```
tests/
├── conftest.py                      # Shared fixtures, test file loader
├── test_workflow_parser.py          # Main parse + convert integration tests
├── test_action_parser.py
├── test_yaml_object_reader.py
├── test_template_reader.py
├── test_file_reference.py
└── testdata/                        # Symlink or copy from original_code
    └── reader/                      # 196 test YAML files
```

**Estimated effort:** ~800 lines Python (test harness + unit tests)

---

## 4. Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| **YAML position tracking** | Medium — wrong line/col breaks error messages | Validate ruamel.yaml position output against TS yaml library early in Phase 2 |
| **Schema edge cases** | Medium — 500+ definitions with subtle interactions | Rely heavily on the 196 test fixtures for regression |
| **Expression library integration** | Low — API mismatch between TS and Python ports | `py-actions-expressions-parser` follows the same Lexer/Parser API; verify with its own test suite |
| **Block scalar handling** | Low-Medium — YAML `\|`, `>`, `\|-` headers affect expression parsing | ruamel.yaml preserves these; test specifically |
| **Circular alias detection** | Low — rare edge case | Port the alias resolution stack from TS |
| **Reusable workflow depth** | Low — async file fetching complexity | Keep sync initially; depth=0 is default |

---

## 5. Suggested Implementation Order & Milestones

### Milestone 1: "Parse a minimal workflow" (Phases 1–2 + partial 4–5)
- Tokens, schema, YAML reader, template reader, workflow parser entry point
- Can parse `on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi`
- Validates against schema, returns token tree with errors

### Milestone 2: "Expression validation works" (Phase 3)
- `py-actions-expressions-parser` integrated into template reader
- `${{ github.ref }}` parses and validates correctly via the library
- `${{ github.event = 12 }}` produces validation error

### Milestone 3: "Full conversion pipeline" (Phase 6)
- `convert_workflow_template()` produces `WorkflowTemplate` output
- Job dependency cycle detection works
- Step auto-ID generation works
- `success() &&` wrapping works

### Milestone 4: "Test suite passes" (Phase 7)
- Test harness reads all 196 fixture files
- Non-skipped tests produce matching output

### Milestone 5: "Action parsing" (remaining from Phase 5–6)
- `parse_action()` works with action-v1.0 schema
- `convert_action_template()` produces `ActionTemplate`

---

## 6. Total Estimated Size

| Component | Python LOC (est.) |
|---|---|
| Tokens | 600 |
| Schema | 700 |
| YAML Object Reader | 400 |
| Expression Integration | 50 |
| Template Reader | 1,200 |
| Template Context + Errors | 300 |
| Workflow/Action Parsers | 300 |
| Model Dataclasses | 400 |
| Converters | 1,800 |
| Tests | 800 |
| **Total** | **~6,550** |

---

## 7. Dependencies to Add (`pyproject.toml`)

```toml
dependencies = [
    "ruamel.yaml>=0.18",                          # YAML parsing with position tracking
    "py-actions-expressions-parser",               # GitHub Actions expression lexer/parser/evaluator
    "croniter>=1.3",                               # Cron expression validation (optional)
]
```

`py-actions-expressions-parser` provides the full expression language support (lexer, parser, AST, evaluator) — no custom expression handling code needed.
