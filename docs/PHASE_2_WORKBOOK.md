# Phase 2 Workbook — Model Boundary and Structured Output

## Block 2.1 — Model interface

### Boundary contract

ArchAgent gives the model separate instructions, the user's question, typed
prior tool interactions, and immutable tool discovery metadata. Tool metadata
contains no registry, executable callable, repository root, or credentials.

The synchronous model interface exposes one operation:

```python
generate(request: ModelRequest) -> ModelResult
```

It is expressed as a structural Python `Protocol`, allowing provider adapters
and test fakes to satisfy the contract without inheriting from an ArchAgent base
class. Shared lifecycle or implementation behavior is not yet demonstrated and
does not justify an abstract base class.

### Requests and context

`ModelRequest` contains separate `instructions`, `question`, `context`, and
`tools` fields. Instructions and question must be nonempty. Context and tools
are immutable tuples and may be empty.

Context retains completed tool interactions rather than flattening them into a
text prompt. Each interaction contains the original structured tool request and
its structured result. Their nonempty opaque request IDs and tool names must
match. Tool arguments are copied into a read-only mapping. This supports future
reconstruction and tracing without giving the model an execution capability.

### Responses

One model response represents exactly one action:

- `TextResponse` contains answer text; or
- `ToolRequest` contains a nonempty opaque ID, nonempty tool name, and arguments.

Distinct immutable response types avoid a single object that could contain both
actions or neither. A tool request is a proposal only. A future harness will
validate it through the registry and decide whether to execute it.

### Configuration and failures

Provider, model, credentials, timeout, retry settings, and the initial output
limit belong to concrete adapter configuration rather than `ModelRequest`.
Credentials must never enter prompts or normal traces. Safe effective settings
can be recorded when tracing is introduced.

Known provider and response problems cross the boundary as immutable
`ModelFailure(code, message, retryable)`. Concrete adapters will translate only
provider errors they understand. Unexpected programming defects propagate as
exceptions. Retry policy belongs to the future harness, not the adapter.

### Test plan

Focused contract tests cover valid and invalid construction, immutability,
read-only copied arguments, request/result correlation, success and failure
observations, both response actions, structural protocol conformance, controlled
model failures, unexpected exceptions, metadata-only tool exposure, and proof
that returning a tool request does not invoke a registry adapter.

Provider adapter behavior and live model calls remain assigned to later Phase 2
blocks.

Final verification on 2026-10-03: all 18 focused model-boundary cases and all
208 repository tests pass. Black, Ruff, and strict mypy also pass. Block 2.1 is
complete.
