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

## Block 3.4 — Context and investigation logs

### Agreed contract and tradeoff

The owner proposed detailed history under `logs/` and a smaller model context
of important facts and references, with the harness selecting result fields
deterministically. Review found that the current fields mainly contain the
evidence itself: directory entries, file contents, search matches, incompleteness
flags, and safe failure information. A path alone is not an observation about
code behavior, and `read_file` cannot currently retrieve a selected line range.

The owner accepted retaining that evidence intact initially, measuring growth,
and rejecting oversized requests rather than silently dropping or summarizing
information. Keep instructions, question, public tool definitions, and all
completed correlated request/result pairs in chronological order. Listings
retain paths/kinds; reading retains path/content; search retains query,
matches with paths and line numbers, skipped files, and truncation status;
failures retain original parameters, code, and safe message. Provider metadata
is recorded in logs but is not inserted into tool-result content.

### Request-size guard

`OllamaConfig.max_request_bytes` is a positive integer with a default of 65,536
bytes (64 KiB). `OllamaModel` measures the complete encoded JSON HTTP body,
including the model field, instructions, question, schemas, history, formatting,
and JSON escaping. The exact limit is allowed; one byte over returns a
non-retryable `context_limit_reached` before network access. This makes the
adapter the owner of provider-specific encoding and the harness the owner of
termination, without adding a size-estimation requirement to the model protocol.

This is an application byte budget, not a tokenizer or a guarantee of fitting
Ollama's allocated token window. It does not configure `num_ctx` or promise that
the provider preserves all input within its own capacity.

### Run logging

`AgentHarness` requires a keyword-only `logs_dir: Path`, supplied by the trusted
caller. For the checkout, use the application-owned `logs/` directory:

```python
harness = AgentHarness(model, registry, instructions, logs_dir=Path("logs"))
```

The repository factory retains its resolved root on the registry so the log
writer can reject direct or symlink-resolved locations inside the inspected
repository before creating anything. Generic registries have no repository
boundary; their caller owns the choice of a trusted destination.

Each run creates one opaque UUID-named `.jsonl` file with exclusive creation.
Question text, arguments, and repository content cannot determine its name.
Records contain the initial instructions/question/tool metadata and limits,
each model attempt's history count and request IDs, model responses including
proposals/failures/metadata, full correlated tool results, and the final outcome.
The ordered records reconstruct the model's provider-independent request
history without duplicating full file contents on every retry or iteration.
These logs are not raw HTTP traces, persistent agent memory, or model-readable
tools. Runtime `/logs/` artifacts are ignored by Git.

Each record is JSON-escaped and flushed before continuing. Known creation,
write, flush, and normal-close failures stop the run with safe `logging_failed`.
No further model or tool call occurs; earlier records are retained. The owner
explicitly chose stopping rather than continuing without a record. Failed logs
may end with a partial record or lack a terminal event; flushing is not an
`fsync` durability guarantee. A normal-close failure can occur after a terminal
record was written, so the caller's `logging_failed` outcome takes precedence.

Unexpected defects remain exceptions. Log their type as `run_interrupted` when
possible and re-raise the original exception even if writing or closing the log
also fails. Exception details and tracebacks are not recorded in this block.

### Verification and observed growth

The owner accepted tests for requests below/at/above the byte limit, growth
after observations, complete and separate run logs, and log-write failures.
Added tests for Unicode/escaping, the entire request rather than just context,
retries without tool re-execution, hostile record content, rejected proposals,
interruption handling, filesystem cleanup/failures, exclusive creation, and
direct/symlink repository-boundary rejection.

All harness tests explicitly use temporary log destinations outside their
target repositories. Verification on 2026-10-11, under the owner's session
pytest authorization: 327 passed and one skipped opt-in live-model check. Black,
Ruff, and strict mypy (including the example script) pass. No live model was
called. The context/log contract is recorded in ADR-0001.

Run the repeatable deterministic example from the project root:

```bash
PYTHONPATH=src uv run python scripts/inspect_context_growth.py
```

The example investigates a temporary fixture with list/read/search tools,
simulates HTTP responses, and writes a full run log under the checkout's
`logs/`. Observed request growth:

| Model round | Completed interactions | Messages | Encoded body bytes |
| --- | --- | --- | --- |
| 1 | 0 | 2 | 1,642 |
| 2 | 1 | 4 | 1,978 |
| 3 | 2 | 6 | 2,302 |
| 4 | 3 | 8 | 2,749 |

These measurements include schemas and JSON escaping and are not token counts.
The scripted answer is not an agent evaluation. An integration test separately
uses a larger file result and a 4,096-byte request limit: the initial call
succeeds, the tool result is fully logged, and the second call is blocked before
network access. Block 3.4 is complete; next is Block 3.5 failure-case review.

## Block 3.5 — Failure cases

### Reviewed contract

The owner confirmed that a missing tool produces `unknown_tool` as a model
observation and consumes one tool attempt. Repeated failed attempts cannot
avoid the default four-attempt limit. After the fourth completed observation,
the model may still return a final answer to the user. A further tool proposal
terminates with `tool_call_limit_reached` before registry invocation.

Controlled tool failures, including permission failures and invalid arguments,
remain observations that permit recovery within the budget. Unexpected model
or tool exceptions stop the run and propagate to the caller. Tests should
verify both propagation and the absence of further model or tool calls.

### Existing coverage reviewed

- `tests/test_agent.py` covers repeated requests, unknown-tool observations,
  exhaustion for tool failures/invalid arguments/unknown tools, recovery from
  invalid arguments, answers at the attempt limit, zero/custom limits,
  run-wide retry exhaustion, and exceptions before or after observations.
- `tests/test_agent_ollama.py` covers actual registry/adapter failure translation,
  invalid argument types and extra fields, repository-boundary failure and
  recovery, and an unexpected tool exception without a follow-up model call.
- `tests/test_agent_logs.py` covers logging of controlled failures and rejected
  proposals, retries without tool re-execution, and stopping on logging failure.

The five failure topics named in this block already have deterministic
coverage. Further configuration review found a termination gap:
`max_model_retries` only rejects negative values, so a fractional float such
as 1.5 is accepted and decrementing it never reaches the equality-to-zero
exhaustion guard. Positive infinity and NaN likewise defeat that guard.
Python's integer annotation does not perform runtime validation.

The owner accepted requiring a non-negative integer and rejecting booleans,
matching the tool-attempt limit contract, and authorized the proposed test
strategy and implementation. Zero permits the initial model attempt without
any retries. Invalid configuration raises `ValueError` at construction before
model/tool calls or log creation.

### Implementation checkpoint

`AgentHarness.__post_init__` now checks the exact integer type before testing
non-negativity. This rejects booleans (which subclass integers), floats,
non-finite values, and incompatible types before comparison or retry arithmetic.

Added nine invalid-input cases: -1, 1.5, 1.0, positive infinity, NaN, `True`,
`False`, `"2"`, and `None`. Added two valid boundary cases with repeated
retryable failures: zero retries gives one model attempt; one retry gives two.
Both return `model_retry_exhausted`, reuse the same request, and execute no
tools. The scripted models contain an extra response so excess retries are
detectable without relying on a live model. Existing default-two-retry and
run-wide budget tests remain in place; the old negative-count case is now
included in the invalid-input group rather than duplicated.

Black, Ruff, strict mypy for source/tests/scripts, and `git diff --check` pass.
The owner ran the full suite on 2026-10-12; no live model was called:

```bash
PYTHONPATH=src uv run pytest -q
```

Observed result: 337 passed and one skipped opt-in live-model check in 0.67s.
Block 3.5 is complete.

## Block 3.6 — Agent tests

Separate evidence of deterministic software correctness from evidence of model
judgment and investigation quality. Begin by classifying these checks and
explaining what each passing result would establish:

1. A scripted model repeatedly requests tools; the harness refuses a fifth
   attempt after four completed tool observations.
2. A real model investigates a small repository to answer where state is
   stored; review whether it selected useful tools and supported its answer
   with inspected evidence.
3. The existing opt-in live Ollama check asks for the word "ready" and asserts
   a nonempty `TextResponse` with valid response metadata.

The owner correctly classified the checks as code test, agent evaluation, and
code test, respectively. Reviewed why the property being measured determines
the classification: the first checks harness enforcement, the second assesses
investigation quality, and the third checks the live adapter's response
contract. Using a real model does not by itself make a check an evaluation.
The live check does not assert that the text is "ready", and it provides no
evidence of useful tool selection or a grounded architectural answer.

### Initial evaluation criteria

The owner asked for help choosing an architectural question. Used a tiny notes
application as the working example: "Where does this application store saved
notes, and which component reads and writes them?" This asks about storage
and responsibility boundaries rather than individual syntax.

The owner accepted requiring both a correct explanation and supporting
inspected code for an evaluation to pass. Assess the final answer for the
storage location and the component responsible for reading/writing. Review
the logged tool results for code supporting those claims; the presence of a
tool call alone does not establish support. A correct guess without supporting
inspection fails this criterion, as does an incorrect answer after inspecting
relevant code. Exact answer wording or a single prescribed tool sequence is
not required.

### Accepted manual review method

The owner selected human review using a short checklist. For the notes-app
question, review these criteria separately:

| Criterion | Passing evidence |
| --- | --- |
| Correct explanation | The answer identifies the actual storage location and the component responsible for reading and writing notes. |
| Support from inspection | Logged tool results contain relevant code supporting those claims; merely listing a filename is insufficient. |

A run passes only when both criteria pass. Different wording and useful tool
sequences are allowed. Use the fixture's known implementation as the reference,
not the model's answer. Establish that reference before reviewing the run.
An execution failure does not pass this task; record its failure code separately
from any answer-quality judgment.

For each future run, retain the question, fixture version, model/configuration,
final outcome, and run-log location. Record pass/fail for each criterion with
a short reason and the supporting log observations. A correct answer without
supporting inspection fails; an incorrect answer despite relevant inspection
also fails. A single passing run provides evidence about that run rather than
a guarantee of consistent performance. Repeated runs can reveal variation.

This is a manual evaluation protocol, not a new deterministic pytest check or
an automated evidence validator. The default pytest suite remains independent
of a running model; the live adapter check remains explicitly opt-in. No
fixture or evaluation runner was added, and no agent evaluation was run.
Actual demo repositories are planned in Block 4.5; the finding schema and
evidence-validation mechanism remain Phase 4 design exercises.

Block 3.6 is complete: the owner distinguished code tests from agent evaluations
and selected initial evaluation criteria and a review method. Phase 3's bounded,
observable loop has deterministic coverage; agent-quality measurements remain
future work. Next is Block 4.1's architectural-finding design.
