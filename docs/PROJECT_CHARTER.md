# Project Charter

## Purpose

ArchAgent is a personal, open-source project for learning how to design, implement, test, secure, observe, and operate a complete agentic AI system.

The learning journey is the product. A smaller implementation whose behavior is understood is more valuable here than a feature-rich implementation assembled from opaque abstractions.

## Product direction

ArchAgent will become an AI architecture investigation and review system. A user will provide a repository and ask questions such as:

- Where does this application store state?
- How is authentication implemented?
- What happens when the database is unavailable?
- Why might the application fail under high concurrency?
- What security, reliability, observability, and testing gaps exist?
- How could agents be introduced responsibly?

ArchAgent should inspect the repository before recommending changes. Its findings should eventually connect claims to the evidence and execution history that produced them.

## Learning objectives

The project should build practical understanding of:

- agents, agent loops, and agent harnesses
- tool contracts, registries, calling, and permissions
- structured model outputs and provider boundaries
- context management, state, and memory
- retrieval, embeddings, and RAG
- planning, delegation, orchestration, and multi-agent systems
- guardrails, human approval, AI security, and prompt-injection defenses
- tracing and observability
- code testing and agent evaluation, including trajectory evaluation
- retries, timeouts, fallbacks, failure handling, and reliability engineering
- deployment and production engineering

## Core principles

### Investigate before recommending

The system should gather repository evidence rather than answer from a question and a superficial repository summary.

### Evidence before confidence

Architectural findings should be traceable to inspected evidence. How this guarantee works is deliberately left as a future design problem.

### Complexity must be earned

Add a component when an observed problem justifies it. Do not begin with vector databases, multi-agent debate, orchestration frameworks, a complex UI, or Kubernetes.

### Mechanics before frameworks

Start with low-level Python and provider APIs so model interaction, tool execution, context, loops, termination, and state remain visible. Compare frameworks only after implementing the primitive mechanisms they abstract.

### Decisions should be explainable

Record significant choices with lightweight architecture decision records covering the problem, options, decision, rationale, and accepted tradeoffs.

## V0.1 boundary

The initial direction is one architect agent investigating a local Python repository through an explicit agent loop and three direct tools:

- `list_files`
- `read_file`
- `search_code`

The owner will define the precise user, problem, input, output, and exclusions during Phase 0. Until then, this is a direction rather than a settled product contract.

## Long-term conceptual direction

The system may eventually include a harness, orchestrator, specialist architecture agents, a shared evidence store, critic agents, and a synthesis agent. This is a destination to test against real needs—not a structure to implement up front.

## Initial technology posture

Prefer:

- Python
- a low-level model SDK/API
- Pydantic or equivalent runtime validation
- pytest
- a CLI

Avoid choosing specific providers, frameworks, storage systems, deployment platforms, or permanent schemas until the relevant design exercise is reached.
