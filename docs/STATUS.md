# Project Status

Last updated: 2026-09-25

## Current position

- **Phase:** 1 — Tool system, without an LLM
- **Block:** 1.2 — File listing
- **State:** `list_files` contract and test plan defined; ready for the first failing test
- **Application code:** None
- **Repository state:** Phase 0 complete; Python project and deterministic quality checks reproduce from a clean checkout

## Next action

Choose the minimal module location for `list_files`, then write the first
failing happy-path test before implementing repository file discovery.

## Current constraints

- Keep Phase 1 free of model calls; tool behavior must be deterministic and testable on its own.
- Begin with the three V0.1 repository tools only: `list_files`, `read_file`, and `search_code`.
- Treat repository paths and contents as untrusted input and keep all access read-only and repository-confined.
- Do not choose an agent framework, model provider, retrieval system, or final finding schema yet.
- Keep the evidence-validation question unresolved until Phase 4 so it remains a genuine design exercise.

## Open questions

- Which minimal source and test modules should contain the first repository
  tool and its result types?
- What is the smallest happy-path test that demonstrates the observable
  `list_files` contract before implementation?
- How should the configured entry limit be supplied without making it a
  model-controlled argument?

## Session log

### 2026-09-25 — `list_files` contract and test design

- Chose explicit, non-recursive directory exploration with a required
  repository-relative path and `"."` for the target root.
- Defined immutable, sorted listing results with normalized paths and file,
  directory, symlink, and other entry kinds.
- Added hidden-entry filtering through an optional `include_hidden` argument and
  deliberately declined to interpret `.gitignore` in V0.1.
- Defined non-following symlink discovery and repository-boundary validation for
  explicitly requested symlink directories.
- Bounded a call at 1,000 examined entries and chose a controlled
  `directory_too_large` failure instead of silent truncation.
- Defined controlled listing failures and tests covering success, filtering,
  ordering, boundaries, security, limits, failures, and unexpected state.
- Documented the Block 1.2 contract and test plan in
  `docs/PHASE_1_WORKBOOK.md`; no application code was added.

### 2026-09-24 — Common repository-tool contract

- Defined an immutable, resolved target-repository boundary and assigned
  filesystem confinement to the repository-tool layer.
- Chose immutable argument metadata and distinct success and controlled-failure
  result types.
- Divided structural request validation from operation-specific path and
  filesystem validation.
- Designed a fixed per-run tool registry with unique names, metadata-only
  discovery, controlled unknown-tool handling, and harness-owned callables.
- Separated safe model-facing errors from internal traceback and absolute-path
  logging.
- Added the policy that an active ArchAgent source checkout cannot be its own
  target, while a non-overlapping clone may be reviewed.
- Documented the contract and its construction, success, failure, boundary,
  security, and read-only test inventory in `docs/PHASE_1_WORKBOOK.md`.
- Completed Block 1.1 and advanced to Block 1.2.

### 2026-09-23 — Phase 0 project setup

- Selected Python 3.12+, `uv`, `uv_build`, and a `src/archagent` package layout.
- Configured Black for formatting, Ruff for linting, mypy in strict mode, and pytest with a package-import smoke test.
- Verified deliberate formatting, linting, and typing failures before applying corrections and confirming passing checks.
- Recreated the project from commit `eef0098` in a temporary clone with `uv sync --locked`; Black, Ruff, mypy, and pytest all passed.
- Completed Phase 0 and advanced to Phase 1, Block 1.1.

### 2026-09-23 — Product and architecture definition

- Completed the V0.1 product definition for one evidence-supported architectural question about a local Python repository.
- Drew and pressure-tested the V0.1 architecture, including loop ownership, run state, failure handling, and read-only repository boundaries.
- Defined Agent, Tool, Model, and Harness responsibilities and traced a file-reading request across their boundaries.
- Advanced to Block 0.4; no application code or tests were added.
- Selected Python 3.12+ to support multiple developer environments, accepting
  the obligation to avoid newer-only features and eventually test supported
  minor versions.

### 2026-09-22 — Planning workspace

- Captured the project purpose, learning philosophy, V0.1 direction, and architecture constraints.
- Created the phased roadmap and Phase 0 workbook.
- Added a persistent AI-collaboration agreement and lightweight ADR process.
- Deliberately made no application architecture or tooling decisions.

## Resume prompt

If useful, begin a future session with:

> Read `AGENTS.md` and `docs/STATUS.md`. Begin Phase 1, Block 1.2 from the
> documented next action. The `list_files` contract and test plan are complete;
> help me choose the minimal module location and write the first failing
> happy-path test before implementation. Update project status when we finish.
