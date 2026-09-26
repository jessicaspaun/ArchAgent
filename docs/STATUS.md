# Project Status

Last updated: 2026-09-25

## Current position

- **Phase:** 1 — Tool system, without an LLM
- **Block:** 1.2 — File listing
- **State:** First `list_files` happy path implemented and passing; remaining contract behavior is incomplete
- **Application code:** Initial immutable listing types and non-recursive happy-path implementation
- **Repository state:** Initial source and test are committed and pushed in `6180a3d`; current files still need formatting and full quality checks

## Next action

Format the first `list_files` implementation and test, run Black, Ruff, mypy,
and pytest with the temporary source-path workaround, then add the next failing
test for hidden-entry behavior.

## Current constraints

- Keep Phase 1 free of model calls; tool behavior must be deterministic and testable on its own.
- Begin with the three V0.1 repository tools only: `list_files`, `read_file`, and `search_code`.
- Treat repository paths and contents as untrusted input and keep all access read-only and repository-confined.
- Do not choose an agent framework, model provider, retrieval system, or final finding schema yet.
- Keep the evidence-validation question unresolved until Phase 4 so it remains a genuine design exercise.

## Open questions

- What persistent development-environment fix should replace the temporary
  `PYTHONPATH=src` workaround for macOS hidden editable-install `.pth` files?
- How should controlled failure result types be represented when the first
  failure test is added?
- Which contract behavior should follow hidden-entry filtering: symlink
  classification, repository confinement, or the entry limit?

## Session log

### 2026-09-25 — First `list_files` red-green cycle

- Added `src/archagent/tools/list_files.py` and
  `tests/tools/test_list_files.py` using a repository-bound `ListFilesTool`.
- Defined `EntryKind`, immutable `ListEntry`, and immutable
  `ListFilesSuccess` records.
- Wrote a first test for sorted, non-recursive file and directory listing and
  observed its expected import and `NotImplementedError` failures.
- Implemented the smallest happy-path directory iteration, relative-path
  conversion, entry classification, sorting, and tuple result.
- Used the failing assertion to find and correct an indentation bug that
  appended only the final directory entry; the owner confirmed the focused
  test passes after the correction.
- Diagnosed a macOS `UF_HIDDEN` interaction that causes Python to skip uv's
  editable-install `.pth` file. Current test commands require the temporary
  `PYTHONPATH=src` workaround until a reproducible project-level fix is chosen.
- Remaining contract behavior and controlled failures are intentionally not yet
  implemented, and the current files still require formatting and full quality
  checks before the next commit.
- The initial source, test, and Block 1.2 documentation were committed and
  pushed as `6180a3d`; follow-up corrections will require another commit.

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
> documented next action. The first `list_files` happy path passes, but the
> files still need formatting and full quality checks. Then help me add the next
> failing test for hidden-entry behavior. Keep using `PYTHONPATH=src` until the
> macOS editable-install issue has a persistent fix, and update project status
> when we finish.
