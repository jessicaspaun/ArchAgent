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

## Block 2.2 — First model interaction

### Provider and transport

The first concrete adapter uses the locally installed `qwen2.5:7b` model through
Ollama. ArchAgent calls Ollama's local `/api/chat` HTTP endpoint directly with
Python's standard library rather than adding the Ollama package. This keeps the
request body, response body, timeout, and translation mechanics visible.

The first interaction is synchronous, text-only, and non-streaming. Adapter
configuration defaults to:

- base URL `http://127.0.0.1:11434`;
- model `qwen2.5:7b`; and
- a 60-second timeout.

The adapter maps instructions to a system message and the question to a user
message. Context and tool definitions return a non-retryable
`unsupported_request` failure before network access because Block 2.2 does not
yet translate those fields. Silently omitting them could produce an answer that
appears grounded without receiving required evidence or capabilities.

### Observed raw response

A direct request to the local endpoint returned assistant text, model name,
completion status, stop reason, input and output token counts, and Ollama timing
fields. The first response contained `"ready"`, 25 input tokens, 2 output
tokens, and stop reason `"stop"`.

Because the live response demonstrated a need for common response data,
`TextResponse` now carries immutable `ResponseMetadata` with model name, input
tokens, output tokens, and stop reason. Provider-specific timing fields remain
outside the core interface; application-level latency will be addressed with
tracing.

### Verification plan and current result

Deterministic tests replace the network function and verify the exact endpoint,
method, header, JSON body, timeout, configured values, response translation,
metadata validation, and rejection of unsupported requests before network
access. HTTP, connection, timeout, and malformed-response ownership remain
explicit exercises for Block 2.4.

The adapter was also invoked once against the installed local model and returned
`TextResponse(text="ready", metadata=...)` with the expected observed values.
Final verification on 2026-10-03: all 220 tests pass. Black, Ruff, and strict
mypy also pass. Block 2.2 is complete.

## Block 2.3 — Structured output

### Native tool-call contract

ArchAgent uses Ollama's native `/api/chat` tool calling rather than asking the
model to imitate a tool call in free-form text. Public `ToolMetadata` is
translated into function definitions with JSON Schema parameters:

- argument types become JSON Schema string or Boolean types;
- required arguments enter the schema's `required` list;
- optional defaults are included in property definitions;
- `nonempty` becomes `minLength: 1`; and
- the tool's extra-argument policy becomes `additionalProperties`.

Repository-relative constraints remain in argument descriptions and are
authoritatively enforced by `ToolRegistry`. JSON Schema guidance cannot prove
filesystem containment.

One model response still represents exactly one action. No tool calls produces
a `TextResponse`. Exactly one tool call with empty response text produces a
`ToolRequest`. Mixed text and tool output, multiple calls, malformed call
structures, or a tool name that was not offered produce a retryable
`invalid_response` failure. No tool is executed by the model adapter.

`ToolRequest` now carries the same provider-independent response metadata as a
text response. The adapter preserves Ollama's nonempty call ID when present and
generates an opaque fallback only when the field is absent.

### Live observations

The first raw Qwen tool response returned one native `list_files` call and no
text. Ollama supplied an ID, but Qwen returned an empty `path` despite the
schema's `minLength: 1`. This is expected model-behavior evidence: schemas guide
generation but do not replace deterministic request validation. The future
harness will submit the request to `ToolRegistry`, which rejects the empty path
before execution.

After implementation, a live call through `OllamaModel` returned a structured
`ToolRequest` with the provider ID, `list_files`, the unmodified empty-path
arguments, and response metadata. It did not execute the tool.

Deterministic tests cover exact schema translation, provider and fallback IDs,
one-call translation, mixed actions, multiple calls, unknown tools, malformed
arguments, and invalid `tool_calls` containers. Black, Ruff, and strict mypy
pass. Final verification on 2026-10-03: all 226 tests pass. Block 2.3 is
complete.

## Block 2.4 — Failure handling

### Ownership and retry guidance

The Ollama adapter translates expected provider and transport failures into
safe, immutable `ModelFailure` values:

| Condition | Code | Retryable |
| --- | --- | --- |
| HTTP 401 or 403 | `authentication_failed` | No |
| HTTP 404 | `model_not_found` | No |
| HTTP 429 | `rate_limited` | Yes |
| HTTP 500–599 | `provider_unavailable` | Yes |
| Other HTTP rejection | `provider_rejected_request` | No |
| Connection failure | `provider_unavailable` | Yes |
| Timeout | `timed_out` | Yes |
| Invalid JSON or response structure | `invalid_response` | Yes |

Failure messages do not include provider response bodies, URLs, prompts,
credentials, filesystem paths, or underlying exception details. HTTP error and
ordinary response streams are closed.

The adapter makes exactly one request. Its `retryable` field is guidance for the
future harness, which will own retry counts, delay, and termination. This keeps
provider translation separate from execution policy.

Only understood failures are converted. An unrelated programming exception
continues to propagate so implementation defects are not disguised as normal
provider conditions.

### Test plan and current result

Deterministic tests cover every HTTP status category, connection refusal,
direct and wrapped timeouts, malformed JSON, missing and incorrectly typed
fields, invalid token counts, safe messages, response closure, one-attempt
behavior, and unexpected exception propagation. Black, Ruff, and strict mypy
pass. Final verification on 2026-10-03: all 241 tests pass. Block 2.4 is
complete.
