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

### Deterministic test plan

Scripted-model tests cover immediate success; one successful tool interaction;
registry and operation-specific tool failures returned as observations; unknown
tools; request/result correlation; rejection of a second tool call; immediate
non-retryable model failure; retry recovery and exhaustion; a shared retry
budget across both logical model requests; fresh state across runs; invalid
configuration and result construction; and unexpected exception propagation.

The owner runs pytest after implementation review. Black, Ruff, and strict mypy
are run by the collaborator before handoff. The owner commands for this block
are:

```bash
PYTHONPATH=src uv run pytest tests/test_agent.py -q
PYTHONPATH=src uv run pytest -q
```

Final verification on 2026-10-04: the owner reported 258 passed and one skipped
opt-in live-model check. Black, Ruff, and strict mypy pass. Block 3.2 is
complete.
