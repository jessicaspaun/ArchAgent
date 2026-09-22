# Phase 0 Workbook — Think Before Coding

Do not research competing products before completing the initial product definition. The point is to make the first mental model your own.

## Block 0.1 — Product definition

Keep each answer to roughly one to three sentences.

### 1. Who is ArchAgent for?

_Your answer:_

### 2. What problem does it solve?

_Your answer:_

### 3. What information can a user give it?

_Your answer:_

### 4. What should it produce?

_Your answer:_

### 5. What explicitly will V0.1 not do?

_Your answer:_

### Challenge notes

After drafting the answers, pressure-test them:

- Is the intended user specific enough to make product decisions?
- Is the problem stated independently of a preferred technology?
- Are inputs and outputs concrete enough to recognize success?
- Does V0.1 have one coherent job?
- Which words are ambiguous and need an operational definition?

_Notes:_

## Block 0.2 — V0.1 architecture

Draw the architecture yourself. The drawing can be Mermaid, ASCII, or an image linked here.

Your diagram should make it possible to ask:

- Where does execution begin and end?
- Which component owns the loop?
- Which boundaries are deterministic and which involve a model?
- How do tool requests and results cross those boundaries?
- Where does repository access occur?
- What state exists during one run?
- What can fail at each boundary?

_Diagram and notes:_

## Block 0.3 — Core concepts in ArchAgent

Define each term in the context of this project—not as a textbook definition.

### Agent

_Your definition:_

### Tool

_Your definition:_

### Model

_Your definition:_

### Harness

_Your definition:_

### Boundary check

Explain how these four concepts differ and where responsibility moves from one to another.

_Your answer:_

## Block 0.4 — Project setup

Only begin this after the earlier Phase 0 exercises have been reviewed.

- [ ] Initialize the Git repository
- [ ] Decide the supported Python version
- [ ] Choose an environment and dependency-management approach
- [ ] Add the smallest justified package structure
- [ ] Configure formatting and linting
- [ ] Configure type checking
- [ ] Configure pytest
- [ ] Confirm the checks run from a clean checkout
- [x] Create the ADR directory and template

Before choosing tools, write down what each tool needs to accomplish and what cost or constraint it introduces.
