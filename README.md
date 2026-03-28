# py-actions-workflow-parser

A Python port of the TypeScript [`@actions/workflow-parser`](https://github.com/actions/languageservices/tree/main/workflow-parser) library. Parses, validates, and converts GitHub Actions workflow YAML files and action manifest files (`action.yml`) into typed Python data structures.

## Features

- **Schema-driven validation** — Validates workflows and actions against the official GitHub Actions JSON schemas, reporting all errors with file/line/column positions
- **Expression validation** — Validates `${{ ... }}` expressions against the allowed context for each field
- **Full data model** — Converts the raw token tree into typed Python dataclasses (`WorkflowTemplate`, `Job`, `RunStep`, `ActionStep`, etc.)
- **Action parsing** — Parses `action.yml` files and converts them into `ActionTemplate` with inputs, outputs, and runs configuration
- **Reusable workflows** — Supports `workflow_call` inputs, secrets, and referenced workflow resolution
- **Faithful port** — Passes the same fixture test suite as the original TypeScript library (85/85 non-skipped tests)

## Installation

```bash
uv add "git+https://github.com/tomasrollo/py_actions_workflow_parser.git"
```

## Quick Start

### Parse a workflow

```python
from py_actions_workflow_parser import (
    parse_workflow,
    convert_workflow_template,
    NoOperationTraceWriter,
)
from py_actions_workflow_parser.workflows.file import File

# Load your workflow YAML
f = File(
    name=".github/workflows/ci.yml",
    content="""
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Hello, world!"
""",
)

# Step 1: parse and validate against the schema
result = parse_workflow(f, NoOperationTraceWriter())

if result.context.errors.count > 0:
    for err in result.context.errors.get_errors():
        print(f"Error: {err.message}")
else:
    # Step 2: convert the token tree into the typed data model
    wt = convert_workflow_template(result.context, result.value)

    for job in wt.jobs:
        print(f"Job: {job.id.value}")
        for step in job.steps:
            print(f"  Step: {step.id}")
```

### Parse an action

```python
from py_actions_workflow_parser import (
    parse_action,
    convert_action_template,
    NoOperationTraceWriter,
)
from py_actions_workflow_parser.workflows.file import File

f = File(
    name="action.yml",
    content="""
name: 'My Action'
description: 'Greet someone'
inputs:
  who-to-greet:
    description: 'Who to greet'
    required: true
    default: 'World'
outputs:
  greeting:
    description: 'The greeting message'
    value: ${{ steps.greet.outputs.message }}
runs:
  using: node20
  main: dist/index.js
""",
)

result = parse_action(f, NoOperationTraceWriter())
if result.context.errors.count == 0:
    at = convert_action_template(result.context, result.value)
    print(f"Action: {at.name}")
    print(f"Inputs: {[i.id for i in at.inputs or []]}")
    print(f"Runs using: {at.runs.using}")
```

## API Reference

### Parsing

#### `parse_workflow(file, context_or_trace) -> TemplateParseResult`

Parses a GitHub Actions workflow YAML file, validates it against the workflow schema, and returns a `TemplateParseResult`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | `str or File` | Path to the workflow file or a File dataclass with name and content workflow file (name + content string) |
| `context_or_trace` | `TraceWriter \| TemplateContext` | Optional trace writer (for simple use) or an existing `TemplateContext` (for advanced use). Can be omitted |

#### `parse_action(file, context_or_trace) -> TemplateParseResult`

Parses a GitHub Actions `action.yml` file, validates it against the action schema, and returns a `TemplateParseResult`.

Same parameters as `parse_workflow`.

#### `TemplateParseResult`

```python
result.context       # TemplateContext — holds errors and file registry
result.value         # TemplateToken | None — the raw parsed token tree
result.context.errors.count        # number of errors
result.context.errors.get_errors() # list[TemplateValidationError]
```

### Conversion

#### `convert_workflow_template(context, root, file_provider?, options?) -> WorkflowTemplate`

Converts the raw token tree from `parse_workflow()` into a typed `WorkflowTemplate`.

```python
wt = convert_workflow_template(result.context, result.value)
```

Options via `WorkflowTemplateConverterOptions`:

```python
from py_actions_workflow_parser import WorkflowTemplateConverterOptions, ErrorPolicy

opts = WorkflowTemplateConverterOptions(
    error_policy=ErrorPolicy.TryConversion,  # convert even if there are parse errors
    max_reusable_workflow_depth=4,
    fetch_reusable_workflow_depth=0,
)
wt = convert_workflow_template(result.context, result.value, options=opts)
```

#### `convert_action_template(context, root, options?) -> ActionTemplate`

Converts the raw token tree from `parse_action()` into a typed `ActionTemplate`.

### Data Model

#### `WorkflowTemplate`

```python
@dataclass
class WorkflowTemplate:
    jobs: list[Job | ReusableWorkflowJob]
    events: EventsConfig | None
    permissions: dict[str, str] | None
    defaults: MappingToken | None
    concurrency: TemplateToken | None
    env: TemplateToken | None
    errors: list[dict[str, str]] | None
```

#### `Job`

```python
@dataclass
class Job:
    type: str          # always "job"
    id: StringToken
    name: ScalarToken | None
    needs: list[StringToken] | None
    if_condition: BasicExpressionToken | None
    permissions: dict[str, str] | None
    runs_on: TemplateToken | None
    steps: list[RunStep | ActionStep]
    env: MappingToken | None
    environment: TemplateToken | None
    strategy: TemplateToken | None
    concurrency: TemplateToken | None
    continue_on_error: bool | TemplateToken | None
    timeout_minutes: TemplateToken | None
    defaults: MappingToken | None
    container: TemplateToken | None
    services: TemplateToken | None
    outputs: MappingToken | None
```

#### Steps

```python
@dataclass
class RunStep:
    id: str
    name: ScalarToken | None
    if_condition: BasicExpressionToken | None
    run: ScalarToken | None
    shell: ScalarToken | None
    working_directory: ScalarToken | None
    env: MappingToken | None
    continue_on_error: bool | ScalarToken | None
    timeout_minutes: ScalarToken | None

@dataclass
class ActionStep:
    id: str
    name: ScalarToken | None
    if_condition: BasicExpressionToken | None
    uses: StringToken | None
    with_: MappingToken | None       # "with" inputs
    env: MappingToken | None
    continue_on_error: bool | ScalarToken | None
    timeout_minutes: ScalarToken | None
```

#### `ReusableWorkflowJob`

```python
@dataclass
class ReusableWorkflowJob:
    type: str          # always "reusableWorkflowJob"
    id: StringToken
    ref: StringToken | None           # the workflow reference (owner/repo/.github/workflows/wf.yml@ref)
    input_values: MappingToken | None
    secret_values: MappingToken | None
    inherit_secrets: bool | None
```

#### `EventsConfig`

```python
@dataclass
class EventsConfig:
    schedule: list[ScheduleConfig] | None
    workflow_dispatch: WorkflowDispatchConfig | None
    workflow_call: WorkflowCallConfig | None
    push: dict[str, Any] | None          # branches, tags, paths filters
    pull_request: dict[str, Any] | None
    pull_request_target: dict[str, Any] | None
    workflow_run: dict[str, Any] | None
    extra: dict[str, Any]                # all other event names
```

#### `ActionTemplate`

```python
@dataclass
class ActionTemplate:
    name: str
    description: str
    author: str | None
    inputs: list[ActionInputDefinition] | None
    outputs: list[ActionOutputDefinition] | None
    runs: ActionRunsComposite | ActionRunsNode | ActionRunsDocker | None
    branding: ActionBranding | None

@dataclass
class ActionRunsNode:
    using: str     # "node12" | "node16" | "node20" | "node24"
    main: str
    pre: str | None
    pre_if: str | None
    post: str | None
    post_if: str | None

@dataclass
class ActionRunsDocker:
    using: str     # "docker"
    image: str
    entrypoint: str | None
    args: list[str] | None
    env: dict[str, str] | None
    # ...

@dataclass
class ActionRunsComposite:
    using: str     # "composite"
    steps: list[RunStep | ActionStep]
```

### Token Type Guards

Token fields on the model contain `TemplateToken` subtypes. Use these guards to narrow them:

```python
from py_actions_workflow_parser import (
    is_string, is_number, is_boolean, is_null,
    is_mapping, is_sequence, is_scalar,
    is_basic_expression, is_insert_expression, is_literal,
)

token = job.runs_on
if is_string(token):
    print(token.value)           # str
elif is_basic_expression(token):
    print(token.expression)      # str — the expression text
elif is_mapping(token):
    for kv in token:
        print(kv.key, kv.value)
```

### Custom Trace Writer

Implement `TraceWriter` to receive debug-level trace events from the parser:

```python
from py_actions_workflow_parser import TraceWriter

class MyTraceWriter:
    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def verbose(self, message: str) -> None:
        pass  # suppress verbose output

result = parse_workflow(f, MyTraceWriter())
```

## Error Handling

Errors are accumulated during parsing without halting. Check `result.context.errors` after parsing:

```python
result = parse_workflow(f, NoOperationTraceWriter())

for error in result.context.errors.get_errors():
    loc = ""
    if error.range:
        loc = f" (Line: {error.range.start.line}, Col: {error.range.start.column})"
    print(f"{error.file_name}{loc}: {error.message}")
```

If there are errors, `result.value` may still be set (the parser recovers and continues). By default, `convert_workflow_template()` returns an empty `WorkflowTemplate` when errors are present. Pass `ErrorPolicy.TryConversion` to convert anyway:

```python
from py_actions_workflow_parser import ErrorPolicy, WorkflowTemplateConverterOptions

opts = WorkflowTemplateConverterOptions(error_policy=ErrorPolicy.TryConversion)
wt = convert_workflow_template(result.context, result.value, options=opts)
```

## Requirements

- Python ≥ 3.13
- [`ruamel-yaml`](https://pypi.org/project/ruamel.yaml/) ≥ 0.19.1
- [`croniter`](https://pypi.org/project/croniter/) ≥ 6.2.2
- `py-actions-expressions-parser` (GitHub: `tomasrollo/py_actions_expressions_parser`)

## Development

```bash
git clone <repo>
cd py_actions_workflow_parser
uv sync
uv run pytest
```

## Background

This library is a Python port of the TypeScript [`@actions/workflow-parser`](https://github.com/actions/languageservices/tree/main/workflow-parser) package, which powers the GitHub Actions language service (editor support for workflow files in VS Code). The Python implementation faithfully replicates the parsing and validation logic, using `ruamel.yaml` for YAML parsing and the companion `py-actions-expressions-parser` library for expression validation.
