# Phase 3 Workbook — First Agent Loop

## Block 3.1 — Define an agent

### Agent definition

In ArchAgent, the agent is the complete system that receives an architectural
question, investigates the configured repository through permitted read-only
tools, and returns a final answer or controlled failure. It is agentic because
the model can propose the next action from observed results while a deterministic
harness controls whether and how those proposals are carried out.

A model using a tool is not, by itself, the ArchAgent agent. The model is the
probabilistic decision-making component; it has no repository or tool-execution
capability. The harness owns the explicit loop, run state, validation routing,
tool execution through the registry, recovery policy, and termination.

### Responsibility boundaries

- The **model** proposes exactly one action: a nonempty final answer or one
  structured tool request. It can use prior structured tool interactions as
  context but cannot execute tools.
- The **harness** constructs model requests, exposes public tool metadata,
  submits proposed calls to the registry, records correlated interactions,
  returns observations to the model, applies deterministic limits and recovery
  policy, and chooses the terminal outcome.
- The **registry** discovers allowed tools, rejects unknown names or invalid
  argument shapes, fills defaults, and invokes only a registered adapter.
- Each **tool** enforces its operation-specific contract, including repository
  containment, and returns a structured success or controlled failure.

Ordinary registry and tool failures become observations so the model can make a
different proposal within the run's limits. The user receives the eventual
answer or terminal controlled failure, not every intermediate observation.
Unexpected programming defects propagate as exceptions instead of being hidden
as ordinary agent failures.

### Harness contract

Given a valid user question, a model, an allowed tool registry, and deterministic
limits, the harness performs a bounded investigation, executes only validated
registered tools, preserves each completed tool interaction as structured
context, and returns either a nonempty final answer or a controlled failure. It
must not allow the model to execute a tool directly or continue without bound.

Run state is initially in-memory process state. It includes the original
question, completed tool interactions, iteration count, and current outcome.
Phase 3 does not add persistent memory or a database; state disappears when the
process exits.

### Verification strategy

Deterministic harness tests will use a scripted fake model rather than relying
on a live model's judgment. The portfolio should cover a direct final answer, a
successful tool-request/observation/final-answer sequence, registry and tool
failures returned as observations, recovery with a different request, model
failures, repeated invalid actions, limit exhaustion, request/result
correlation, and unexpected exception propagation.

Whether a real model chooses useful tools, investigates enough evidence, or
answers an architectural question well is an agent-evaluation concern, not a
deterministic proof of loop correctness.

Block 3.1 was completed on 2026-10-04 by reconciling the Phase 0 definitions
with the implemented Phase 1 tool boundary and Phase 2 model boundary. No
application code changed.

## Block 3.2 — Single tool call

Design and implement the smallest explicit path from question to model tool
request, registry execution, structured observation, and final model answer.

### Agreed contract

The harness is reusable configuration containing a model, allowed registry,
nonempty agent instructions, and a maximum model-retry count. Every `run` starts
fresh in-memory state with the supplied nonempty question, no prior context, and
the full retry budget. Tool history and retry state never cross between runs.

One run accepts either of these paths:

1. the first model request returns a nonempty final answer, which is returned
   immediately; or
2. the first model request proposes one tool, the registry validates and invokes
   it, the success or controlled failure becomes one structured interaction, and
   the second model request returns the final answer.

A second sequential tool proposal is not executed in this block. It produces
`tool_call_limit_reached`; Block 3.3 will deliberately replace that one-call
limit with bounded iterative investigation. Immediate answers remain allowed.
The harness does not yet claim that an answer is grounded.

The public result is either `AgentSuccess(answer)` or
`AgentFailure(code, message)`. It does not expose chain-of-thought, repeat the
local repository path, or act as a partial execution trace.

Retryable model failures share one run-wide budget of two retries by default.
The harness retries the same model request without adding provider failures to
model context. A recovered call continues with the remaining budget; success
does not replenish it. Exhaustion produces `model_retry_exhausted`.
Non-retryable model failures retain their safe code and message and terminate
immediately. Unexpected model or tool exceptions propagate.

### Ollama context translation

The owner defined the adapter contract to preserve success/failure, successful
response data, failure codes, and the original parameters. The completed
contract also retains the tool name, correlated request/result ID, safe failure
message, and ordering.

Each completed interaction becomes an assistant message containing the original
tool call, followed by a tool message containing its outcome. The assistant
call carries `id`, function `name`, and `arguments`; the result carries
`tool_name`, matching `tool_call_id`, and JSON text in `content`:

- Success: `{"status": "success", "data": ...}` with all existing success
  dataclass fields, including search matches, skipped files, and truncation.
- Controlled failure: `{"status": "failure", "error": {"code": ..., "message": ...}}`.

Instructions and the original question precede those messages. The adapter
translates observations but does not execute tools, revalidate parameters, or
choose retries. Incorrect parameters are rejected by the registry and returned
as controlled observations. Unexpected tool exceptions propagate before a
follow-up model request is constructed.

This follows [Ollama's documented tool-call sequence](https://docs.ollama.com/capabilities/tool-calling)
and its [native message and tool-call fields](https://github.com/ollama/ollama/blob/main/api/types.go).
Repository text remains inside tool-result content; this structural separation
does not prove that a model resists prompt injection.

### Deterministic test plan

Scripted-model tests cover immediate success; one successful tool interaction;
registry and operation-specific tool failures returned as observations; unknown
tools; request/result correlation; rejection of a second tool call; immediate
non-retryable model failure; retry recovery and exhaustion; a shared retry
budget across both logical model requests; fresh state across runs; invalid
configuration and result construction; and unexpected exception propagation.

Adapter tests cover all three success result types, an empty listing, untrusted
text and Unicode preservation, controlled failures, and connection failure with
context. Deterministic integration tests use the actual harness, Ollama
adapter, registry, and repository reader with simulated HTTP responses. They
cover successful reading, provider and generated IDs, missing files,
empty/mistyped/extra parameters, and unexpected tool errors stopping the run
without a second model call. They check translated messages, not model quality.

The owner normally runs pytest after implementation review. Black, Ruff, and
strict mypy are run by the collaborator before handoff. Commands for this block:

```bash
PYTHONPATH=src uv run pytest tests/test_ollama.py tests/test_agent_ollama.py tests/test_agent.py -q
PYTHONPATH=src uv run pytest -q
```

Verification on 2026-10-04: the owner reported 258 passed and one skipped opt-in
live-model check. Black, Ruff, and strict mypy pass. A subsequent code walkthrough
found an integration gap: `OllamaModel.generate()` still returns
`unsupported_request` whenever `ModelRequest.context` is nonempty. The harness's
second request therefore works with the scripted model but not with the real
adapter. Block 3.2 was reopened pending context translation and cross-boundary
tests.

Verification on 2026-10-11: the owner explicitly asked the collaborator to run
pytest this session. The focused suite reports 57 passed; the full suite reports
270 passed and one skipped opt-in live-model check. Black, Ruff, and strict mypy
pass. The translation and deterministic integration gap is resolved; Block 3.2
is complete. No live model was called, and model investigation quality remains
an evaluation concern.

## Block 3.3 — Multiple tool calls

### Agreed contract

The owner chose a configurable tool-attempt limit, defaulting to four, with
failed and repeated requests consuming the budget. After the last allowed
attempt, the model gets an opportunity to return a final answer.

`AgentHarness.run()` now loops over one model action at a time:

1. Construct a request with the original instructions, question, tool metadata,
   and all completed interactions in chronological order.
2. Generate a response using the remaining run-wide model-retry budget.
3. Return a nonempty text answer or terminal model failure immediately.
4. For a tool proposal, check the attempt limit before invoking the registry.
   If exhausted, return `tool_call_limit_reached` without executing or adding
   an observation for the excess proposal.
5. Otherwise invoke the registry, retain the correlated success or controlled
   failure, and continue.

The limit counts registry attempts, including invalid parameters, unknown tools,
operation-specific failures, and repeated calls with identical parameters.
Provider failures and retries do not consume tool attempts. Retries use the same
model request and do not re-execute an already completed tool. A successful
iteration does not replenish either budget.

Text answers are accepted before checking the tool budget so the last allowed
observation can lead to an answer. Tools remain offered on that last model
request; if the model proposes another call, the harness enforces termination.
With tool limit N and model retry budget R, the run makes at most N + 1 logical
model requests and N + 1 + R model attempts. Default limits permit at most four
registry attempts and seven model attempts. This bounds execution, not answer
quality or the model's willingness to finish.

The configurable limit must be a non-negative integer; booleans, negative
values, floats, and strings are rejected. Zero allows an immediate answer but
rejects any tool proposal. Every run starts with fresh history and both budgets.
Unexpected model or tool exceptions propagate immediately.

History is retained as immutable tuple snapshots. Earlier model requests do not
change when later interactions are appended. No context selection, truncation,
summarization, or persistent storage is introduced here; observing context
growth remains Block 3.4.

### Deterministic test plan

The owner proposed successful investigations below and at the limit, failed
tool calls, repeated calls, and an attempted fifth call. Added boundary and
cross-component coverage for custom limits (one and six), zero attempts,
invalid settings, invalid-argument recovery, exhausted failure budgets,
later model failures, retries on the final answer opportunity, exceptions
after prior observations, and fresh state across runs.

Harness tests use scripted models and recording tools. Integration tests use
the real harness, Ollama adapter, registry, and repository tools with simulated
HTTP responses. They cover list/search/read sequences below and at four calls,
an excess request without execution, full ordered transcript preservation, and
recovery after a real repository-boundary failure without exposing outside
file contents.

Verification on 2026-10-11: after adding the new contracts, the old single-call
implementation reported 20 expected failures and 15 passes. The bounded-loop
implementation then passed the focused tests. The owner authorized
collaborator-run pytest for this session; final verification reports 81 focused
tests passed and 294 passed with one skipped live-model check in the full
suite. Black, Ruff, and strict mypy pass. No live model was called. Block 3.3 is
complete; the next exercise is Block 3.4 context design.
