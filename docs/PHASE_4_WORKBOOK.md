# Phase 4 Workbook — Evidence-based Architecture Analysis

## Block 4.1 — Architectural finding

### Opening exercise

The current harness returns a text answer or controlled failure. The V0.1
product promises an explanatory answer supported by repository evidence and
identifies relevant risks or uncertainties. Design a finding representation
that helps a reader assess an architectural claim.

Start with the owner’s proposal:

- What information should one architectural finding contain?
- What contract does this component promise to callers and readers?
- What tests would convince you this works?

Use the notes-app storage question from Block 3.6 as a concrete example. Keep
an observation about existing architecture distinct from a recommendation
about changing it; not every finding needs to identify a defect.

Review happy paths, boundaries, invalid inputs, failures, security concerns,
unexpected state, and dependency failures as applicable before generating
tests. Separate deterministic validation of a finding's shape from evaluating
the quality of its claims.

No schema is selected. Provenance design belongs to Block 4.2, architect
behavior to Block 4.3, evidence validation to Block 4.4, and demo repositories
to Block 4.5. Note needs for those blocks without settling their mechanisms.
