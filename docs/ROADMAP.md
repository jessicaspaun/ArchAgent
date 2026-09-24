# ArchAgent Learning Roadmap

This roadmap is ordered to expose engineering problems before introducing abstractions that solve them. Estimates are learning-time guides, not deadlines. A block is complete when its intended concept can be explained and its behavior has been demonstrated—not merely when code exists.

## Progress legend

- `[ ]` not started
- `[~]` in progress
- `[x]` complete

The canonical current position and next action live in [STATUS.md](STATUS.md).

## Phase 0 — Think before coding (~4 hours)

- [x] **0.1 Product definition** — define the user, problem, accepted input, output, and explicit V0.1 exclusions.
- [x] **0.2 V0.1 architecture** — draw the architecture and defend component boundaries and failure ownership.
- [x] **0.3 Core concepts** — define agent, tool, model, and harness in ArchAgent's own terms.
- [x] **0.4 Project setup** — initialize the repository and establish the minimal Python, formatting, linting, typing, testing, and ADR workflow.

Exit condition: the owner can explain what V0.1 is, how its major pieces interact, and why its initial development environment was chosen.

## Phase 1 — Tool system, without an LLM (~7 hours)

- [~] **1.1 Tool contract** — decide what tools expose, receive, return, how errors appear, and how discovery and invocation work.
- [ ] **1.2 File listing** — define behavior and tests, then implement repository file discovery.
- [ ] **1.3 File reading** — design and implement safe repository file access, including boundaries and failures.
- [ ] **1.4 Code search** — implement lexical repository search; no semantic or vector search.
- [ ] **1.5 Tool registry** — design discovery and invocation without a growing conditional chain.
- [ ] **1.6 Tool testing** — review unit, integration, failure, and security-related coverage.
- [ ] **1.7 Refactor** — add no behavior; extract only abstractions demonstrated by existing code.

Exit condition: tools can be discovered and invoked through a tested contract without any model involvement.

## Phase 2 — Model boundary and structured output (~5 hours)

- [ ] **2.1 Model interface** — design a boundary that does not fundamentally bind ArchAgent to one provider.
- [ ] **2.2 First model interaction** — make and inspect the simplest request and response before hiding details.
- [ ] **2.3 Structured output** — require and validate machine-readable model output.
- [ ] **2.4 Failure handling** — explore malformed output, missing fields, timeouts, and provider errors; assign ownership.
- [ ] **2.5 Model tests** — design deterministic model-boundary tests without relying on live calls for every run.

Exit condition: model-facing behavior has an explicit, provider-conscious contract with understood failure paths.

## Phase 3 — First agent loop (~6 hours)

- [ ] **3.1 Define an agent** — decide what makes this system an agent rather than a chatbot and record the decision.
- [ ] **3.2 Single tool call** — implement question → model → tool request → execution → observation → model → answer.
- [ ] **3.3 Multiple tool calls** — permit iterative investigation and encounter termination problems deliberately.
- [ ] **3.4 Context** — decide what returns to the model each iteration and observe context growth.
- [ ] **3.5 Failure cases** — exercise repeated calls, missing tools, invalid arguments, tool exceptions, and nontermination.
- [ ] **3.6 Agent tests** — separate deterministic loop tests from probabilistic agent evaluations.

Exit condition: a bounded, observable loop can investigate through tools and fail in understood ways.

## Phase 4 — Evidence-based architecture analysis (~5 hours)

- [ ] **4.1 Architectural finding** — design the finding schema.
- [ ] **4.2 Provenance** — define how findings reference repository evidence.
- [ ] **4.3 Architect behavior** — define the architect agent's responsibilities and boundaries.
- [ ] **4.4 Evidence validation** — design how the system verifies that cited evidence was actually inspected.
- [ ] **4.5 Demo repositories** — build small, deliberately flawed applications as fixtures for tests and evaluations.

Exit condition: ArchAgent produces findings whose provenance can be checked against its actual investigation.

## Phase 5 — RAG (~7 hours)

- [ ] **5.1 Retrieval fundamentals** — explain documents, chunks, embeddings, vectors, similarity, retrieval, and context.
- [ ] **5.2 Ingestion** — turn repository information into retrievable documents and chunks.
- [ ] **5.3 Embeddings** — generate and store embeddings.
- [ ] **5.4 Retrieval** — retrieve repository context for a question.
- [ ] **5.5 Agent integration** — reason about when to use direct tools versus retrieval.
- [ ] **5.6 Retrieval testing** — create known queries and expected relevant results; measure performance.
- [ ] **5.7 Failure analysis** — vary chunking and content to study misleading matches, ambiguity, noise, and misses.

Exit condition: retrieval quality is measured, its failure modes are demonstrated, and its role relative to direct tools is justified.

## Phase 6 — Tracing and observability (~4 hours)

- [ ] **6.1 Define a trace** — draw the desired representation of one complete execution.
- [ ] **6.2 Instrument execution** — capture requests, model calls, tools, retrieval, latency, tokens, and errors.
- [ ] **6.3 Observability platform** — compare the internal trace model with an appropriate external platform.
- [ ] **6.4 Trace-based debugging** — introduce bad behavior and diagnose it primarily through traces.

Exit condition: an investigation can be reconstructed and a deliberately introduced problem can be diagnosed from telemetry.

## Phase 7 — Extract the agent harness (~5 hours)

- [ ] **7.1 Find the seam** — distinguish ArchAgent-specific components from infrastructure most agents need.
- [ ] **7.2 Agent configuration** — design reusable configuration from observed needs.
- [ ] **7.3 Extract infrastructure** — separate common execution, model, tool, and context behavior.
- [ ] **7.4 Second use case** — build a trivial different agent and use its friction as design feedback.
- [ ] **7.5 Refactor and test** — stabilize the harness contracts.

Exit condition: the harness is explained in terms of concrete duplication and pain it removes.

## Phase 8 — Multi-agent architecture (~6 hours)

- [ ] **8.1 Agent boundaries** — justify each specialist against alternatives such as a tool, prompt, function, or deterministic component.
- [ ] **8.2 Second agent** — add only one justified specialist.
- [ ] **8.3 Handoffs** — define delegation and the information crossing agent boundaries.
- [ ] **8.4 Orchestrator** — route work to the appropriate specialist.
- [ ] **8.5 Parallelism and state** — experiment with simultaneous investigation and controlled shared state/evidence.
- [ ] **8.6 Multi-agent testing** — classify routing, handoff, state, failure propagation, and selection checks as tests or evals.

Exit condition: every agent boundary has a demonstrated reason to exist, and coordination behavior is verifiable.

## Phase 9 — Guardrails and security (~5 hours)

- [ ] **9.1 Threat model** — model threats while treating repositories as untrusted input.
- [ ] **9.2 Prompt injection** — place malicious instructions in a repository and observe the system's behavior.
- [ ] **9.3 Tool permissions** — design capability boundaries for tools and agents.
- [ ] **9.4 Human in the loop** — add a dangerous action that requires explicit approval.
- [ ] **9.5 Security testing** — build adversarial tests that go beyond prompt-only defenses.

Exit condition: important trust boundaries and abuse cases are documented and enforced by more than model instructions.

## Phase 10 — Agent evaluations (~6 hours)

- [ ] **10.1 Define quality** — make good ArchAgent performance operational and measurable.
- [ ] **10.2 Evaluation dataset** — manually create 10–20 representative tasks.
- [ ] **10.3 Final-answer evaluation** — assess architectural answer quality.
- [ ] **10.4 Groundedness and evidence** — assess whether claims are supported by inspected evidence.
- [ ] **10.5 Trajectory evaluation** — assess the investigation process, not only the final response.

Exit condition: repeatable evaluations reveal meaningful regressions in answer quality, grounding, or investigation behavior.

## Later phases to define when earned

The charter also calls for deeper reliability and production engineering: retries, timeouts, fallbacks, deployment, operations, and production validation. Their detailed phases should be designed after Phase 10, using the architecture and observed failures that actually exist at that point rather than guessed requirements today.
