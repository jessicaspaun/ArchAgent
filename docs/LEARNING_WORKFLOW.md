# Learning Workflow

## How a block should run

Each roadmap block follows a small learning loop:

1. **Frame the problem.** State what is being learned and what is deliberately out of scope.
2. **Define the contract.** Ask what behavior the component promises to callers.
3. **Propose a design.** The project owner sketches the solution before receiving one.
4. **Pressure-test it.** Challenge assumptions, failure modes, edge cases, security boundaries, and ownership.
5. **Design verification.** Ask what tests or evaluations would provide convincing evidence.
6. **Implement the smallest useful version.** Keep the mechanics visible.
7. **Review evidence.** Run tests, inspect behavior, and compare results with the contract.
8. **Reflect.** Record surprises, unresolved questions, and significant decisions.
9. **Update status.** Mark the block complete only when its learning outcome—not merely its code—is complete.

## Help escalation

Assistance should increase only as needed:

1. **Questions** — prompts that help the owner identify the issue.
2. **Conceptual hint** — the relevant idea or topic to investigate.
3. **Strong hint** — the likely problematic abstraction, component, or decision.
4. **Pseudocode** — the shape of a solution without production code.
5. **Implementation** — working code when explicitly requested or after genuine struggle.

## Testing prompts

Before writing tests, answer:

> What contract does this component promise?

Then:

> What tests would convince you this works?

Consider, without treating this as a mechanical checklist:

- happy paths
- boundary conditions
- invalid inputs
- dependency and operating-system failures
- unexpected state
- security abuse and hostile input
- recovery and cleanup behavior

## Code tests versus agent evaluations

| Question | Code tests | Agent evaluations |
|---|---|---|
| Primary concern | Is the software behaving correctly? | Is the AI system behaving well? |
| Typical properties | Deterministic contracts and failure behavior | Quality, judgment, grounding, and trajectory |
| Examples | Unit, contract, integration, end-to-end, failure, security | Completion, groundedness, evidence quality, tool selection, tool arguments, unnecessary calls, hallucination |

A mocked model test can prove the loop handles a tool request correctly. It cannot, by itself, prove that a real model will choose the right tool for an architectural investigation. The latter needs an evaluation.

## End-of-session routine

Before stopping:

1. Update `docs/STATUS.md` with the current block and exact next action.
2. Record test/evaluation results or current blockers.
3. Add an ADR only if a significant decision was actually made.
4. Leave unfinished questions visible instead of silently resolving them.

This routine is what makes the project easy to resume after a long break.
