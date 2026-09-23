# Project Status

Last updated: 2026-09-23

## Current position

- **Phase:** 0 — Think before coding
- **Block:** 0.4 — Project setup
- **State:** In progress
- **Application code:** None
- **Repository state:** Git initialized; product definition, V0.1 architecture, and core concepts documented

## Next action

Decide the supported Python version. Before selecting the environment and dependency-management approach, state what that tooling must accomplish and what costs or constraints matter for this learning project.

## Current constraints

- Do not begin Phase 1 application code before completing the Block 0.4 setup decisions and checks.
- Do not choose an agent framework, model provider, retrieval system, or final finding schema yet.
- Keep the evidence-validation question unresolved until Phase 4 so it remains a genuine design exercise.

## Open questions

- Which Python version should the project support, and why?
- What should manage the virtual environment and dependencies?
- What is the smallest justified package layout?
- Which formatting, linting, typing, and testing tools meet the project's learning goals without hiding mechanics?

## Session log

### 2026-09-23 — Product and architecture definition

- Completed the V0.1 product definition for one evidence-supported architectural question about a local Python repository.
- Drew and pressure-tested the V0.1 architecture, including loop ownership, run state, failure handling, and read-only repository boundaries.
- Defined Agent, Tool, Model, and Harness responsibilities and traced a file-reading request across their boundaries.
- Advanced to Block 0.4; no application code or tests were added.

### 2026-09-22 — Planning workspace

- Captured the project purpose, learning philosophy, V0.1 direction, and architecture constraints.
- Created the phased roadmap and Phase 0 workbook.
- Added a persistent AI-collaboration agreement and lightweight ADR process.
- Deliberately made no application architecture or tooling decisions.

## Resume prompt

If useful, begin a future session with:

> Read `AGENTS.md` and `docs/STATUS.md`. Continue Block 0.4 from the documented next action. Follow the learning workflow: ask me to state the tooling contract and constraints before recommending setup choices, and update project status when we finish.
