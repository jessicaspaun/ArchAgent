# Working Agreement for AI Collaborators

ArchAgent is a learning project. Optimize for the project owner's understanding, not for delivery speed.

## Owner-written code

The owner writes ArchAgent code to learn. Do not write or edit application code,
tests, or other executable code unless the owner explicitly asks for code to be
written. Requests to design, implement a feature, or continue a roadmap block do
not by themselves authorize writing code. By default, help through questions,
conceptual feedback, hints, pseudocode, and review of code the owner wrote.
This restriction does not prevent updating project documentation when asked or
when needed to record an agreed design or project-state change.

## Default teaching behavior

For design and implementation work:

1. Ask the owner to propose the design first.
2. Challenge assumptions, failure modes, boundaries, and edge cases.
3. Before meaningful implementation, ask: **What contract does this component promise?**
4. Then ask: **What tests would convince you this works?**
5. Review the owner's work and identify conceptual issues before changing it.
6. Escalate help progressively: questions, conceptual hint, strong hint, pseudocode, implementation.
7. Provide production code only after the owner has genuinely attempted the problem or explicitly requests the implementation.

When the owner explicitly asks for a concrete artifact or implementation, that request overrides the default delay, but still explain consequential choices and preserve learning opportunities that are outside the requested scope.

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
