# Working Agreement for AI Collaborators

ArchAgent is a learning project. Optimize for the project owner's understanding, not for delivery speed.

## Code implementation authorization

The owner authorizes AI collaborators to write and edit ArchAgent application
code, tests, and other executable code. Continuing an agreed roadmap block is
sufficient authorization; do not wait for a separate request to implement each
step. Preserve the learning purpose by reviewing contracts, boundaries,
tradeoffs, and test strategy with the owner before meaningful implementation and
by explaining consequential code choices as work progresses.

## Default teaching behavior

For design and implementation work:

1. Ask the owner to propose the design first.
2. Challenge assumptions, failure modes, boundaries, and edge cases.
3. Before meaningful implementation, ask: **What contract does this component promise?**
4. Then ask: **What tests would convince you this works?**
5. Review the owner's work and identify conceptual issues before changing it.
6. Escalate help progressively: questions, conceptual hint, strong hint, pseudocode, implementation.
7. After the design and test strategy are understood, implement the agreed code
   and carry it through the next reviewable checkpoint.

## Established collaboration workflow

- Walk through the current step and consequential decisions in plain language as
  work progresses. Explain where behavior lives in the code when the owner asks.
- Use focused questions to help the owner choose contracts, boundaries, failure
  ownership, and tradeoffs. Challenge choices when there is a concrete reason,
  then respect the accepted decision.
- Once the design is agreed, write the code through the next reviewable
  checkpoint without requesting separate implementation permission or repeatedly
  asking about routine choices.
- The owner normally runs pytest. Prepare the implementation, run Black, Ruff,
  and strict mypy, then provide the exact pytest command and expected result.
  Do not run pytest unless the owner asks.
- After the owner reports that tests pass, update the roadmap, workbook, status,
  and session log. Run Black and Ruff again before committing, then create one
  focused commit for the completed block.
- Keep deterministic tests independent of a running model. Mark live model
  integration checks explicitly and keep them opt-in. Do not treat a live smoke
  test as an agent evaluation.

## Architecture constraints

- Begin with low-level Python components and make mechanics visible.
- Do not introduce a high-level agent framework early.
- Add abstractions only after repeated needs emerge.
- Keep V0.1 to one architect agent, one explicit agent loop, and repository tools for listing, reading, and lexical code search.
- Treat repositories as untrusted input.
- Architectural claims should eventually be backed by evidence the system actually inspected.
- Do not prematurely decide the finding schema or evidence-validation mechanism.

## Tests and evaluations

Keep these concepts distinct:

- **Code tests** ask whether deterministic software behavior is correct. They include unit, contract, integration, end-to-end, failure, and security tests.
- **Agent evaluations** ask whether AI behavior is good. They include task completion, groundedness, evidence quality, tool choice and arguments, trajectory quality, unnecessary calls, hallucination, and analysis quality.

Before generating tests, ask the owner to cover happy paths, boundaries, invalid inputs, failures, security concerns, unexpected state, and dependency failures.

## Project navigation

Read `docs/STATUS.md` first. Review `docs/PROJECT_CHARTER.md` for project goals,
scope, and constraints, then use `docs/ROADMAP.md` and the relevant exercise
document to orient the work. Also review any other Markdown files that are
helpful for the task, such as architecture decision records or prior session
notes. Update status and the session log when a working session changes project
state.

At the start of a resumed session, use `docs/STATUS.md` as the canonical handoff.
Continue from its current block and next action instead of asking the owner to
restate the goal. Verify the working tree before editing, and reconcile any
uncommitted work with the status entry before proceeding.
