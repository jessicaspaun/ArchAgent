# ArchAgent

ArchAgent is a personal, open-source learning project for building a production-style agentic AI system from first principles.

The eventual product will investigate software repositories and answer architecture questions with traceable repository evidence. The immediate goal is not to build that final system quickly. It is to learn the engineering concepts by introducing them one at a time, experiencing the problems they solve, and documenting the decisions made along the way.

## Current status

Planning only. No application code or architecture decisions have been made yet.

Start here when returning to the project:

1. Read [Project Status](docs/STATUS.md).
2. Continue the current exercise in the [Phase 0 Workbook](docs/PHASE_0_WORKBOOK.md).
3. Use the [Roadmap](docs/ROADMAP.md) to understand what comes next.
4. Record meaningful design choices as lightweight [architecture decision records](docs/decisions/README.md).

## V0.1 direction

The first useful version will accept a local Python repository and let one architect agent investigate architectural questions using a deliberately small tool set:

- list repository files
- read a repository file
- search repository code

The agent should investigate before answering and support its architectural claims with evidence. The exact contracts, schemas, and mechanisms are intentionally undecided; designing them is part of the project.

## Project documents

- [Project Charter](docs/PROJECT_CHARTER.md) — purpose, principles, scope, and long-term direction
- [Roadmap](docs/ROADMAP.md) — phased learning and implementation plan
- [Learning Workflow](docs/LEARNING_WORKFLOW.md) — how design, hints, implementation, testing, and evaluation should work
- [Phase 0 Workbook](docs/PHASE_0_WORKBOOK.md) — the first exercises, intentionally left for the project owner to complete
- [Project Status](docs/STATUS.md) — current position, next action, and session log
- [ADR Guide](docs/decisions/README.md) — how to record significant decisions

## Guiding constraint

Complexity must be earned. V0.1 starts with Python, a model API/SDK, structured validation, pytest, and a CLI. Frameworks, RAG, multi-agent orchestration, and production infrastructure come later, after their underlying problems are understood.
