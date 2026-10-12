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

The finding's outer shape is defined below. Provenance design belongs to Block 4.2, architect
behavior to Block 4.3, evidence validation to Block 4.4, and demo repositories
to Block 4.5. Note needs for those blocks without settling their mechanisms.

### Initial owner proposal

The owner proposed supporting files, line numbers, and the locations where
data is read elsewhere. These capture evidence locations and relationships
between components. The collaborator suggested including the architectural
claim itself so a reader knows what those locations support. The proposal is
not yet an agreed schema.

### Agreed conceptual contract

The owner accepted: "A finding states a clear architectural claim, identifies
supporting code locations, and makes gaps in its evidence explicit." The three
conceptual pieces are claim, evidence, and limitations. For example, finding a
reader without identifying a writer supports reporting that the writer was
not identified; it does not establish that no writer exists.

This is the intended meaning of a finding, not a claim that shape validation
can prove factual correctness or actual inspection. Deterministic schema
tests check representation rules. Human evaluation assesses claim quality;
the inspection-validation mechanism remains Block 4.4.

### Finding schema and verification plan

The owner accepted requiring at least one supporting location and allowing
an empty limitations collection when there are no known gaps.

| Field | Meaning | Rule |
| --- | --- | --- |
| `claim` | One architectural statement about the repository | Required text; empty or whitespace-only text is invalid. |
| `evidence` | Supporting code-location references | Required collection with at least one reference; its entry structure is the Block 4.2 exercise. |
| `limitations` | Explicit gaps in the investigation's support | Collection of nonblank statements; may be empty. |

Follow the project's existing immutable result-object pattern: a frozen record
with tuple collections. Preserve the supplied meaningful text, all evidence
references, and the order of limitations. Do not add severity, confidence
scores, or mandatory recommendations without a demonstrated need.

Discussed deterministic verification cases:

- A valid claim with one supporting location and no limitations succeeds.
- Multiple locations and explicit limitations are retained.
- Missing/empty/whitespace-only claims and absent evidence are rejected.
- Wrong field/element types and blank limitation statements are rejected.
- Findings cannot be mutated; mutable input collections must not create an
  avenue to change an already constructed finding.

Detailed evidence-path and line-range cases belong to Block 4.2. This object
is a data representation with no model calls, repository reads, or external
dependencies; filesystem/dependency failures are not construction behavior.
Treat all supplied text as data. Construction does not establish file
existence, prove the truth of claims, or validate actual inspection.

Block 4.1's schema-design exercise is complete. No executable code or tests
were added; implement the record after its evidence-reference type has an
agreed contract and verification plan in Block 4.2. The last passing code
suite is unchanged.

## Block 4.2 — Provenance

### Opening exercise

Define the evidence entry used by a finding. The owner's initial proposal
included supporting files and line numbers. First choose whether one location
points to a single line or an inclusive start/end range that can cover the
code supporting a claim. Then review repository-relative path representation,
range boundaries, and invalid inputs.

What contract does an evidence reference promise, and what tests would
convince the owner it works? Keep structural validation distinct from checking
that the cited repository evidence exists and was inspected; the latter
mechanism remains Block 4.4. No evidence-reference schema is selected yet.
