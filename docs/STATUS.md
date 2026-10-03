# Project Status

Last updated: 2026-10-03

## Current position

- **Phase:** 1 — Tool system, without an LLM
- **Block:** 1.4 — Code search (next; design not started)
- **State:** Block 1.3 is complete; the owner confirmed the full test suite passes; Black, Ruff, and mypy pass
- **Application code:** `ReadFileTool` returns immutable caller-path and exact-content results, confines resolved paths to the repository, rejects non-regular targets, reads at most 256 KiB plus one byte, and handles size, NUL, UTF-8, missing-path, non-file, and permission failures. `list_files` is complete.
- **Repository state:** Block 1.2 is committed in `39e490b`. Block 1.3 completion includes file-reading source, tests, and contract documentation.

## Next action

Begin Block 1.4 by defining the `search_code` contract and test inventory.
Decide query semantics, search scope, match output, traversal and symlink rules,
resource limits, and failure behavior before implementation. Keep search lexical.

## Current constraints

- Keep Phase 1 free of model calls; tool behavior must be deterministic and testable on its own.
- Begin with the three V0.1 repository tools only: `list_files`, `read_file`, and `search_code`.
- Treat repository paths and contents as untrusted input and keep all access read-only and repository-confined.
- Do not choose an agent framework, model provider, retrieval system, or final finding schema yet.
- Keep the evidence-validation question unresolved until Phase 4 so it remains a genuine design exercise.

## Open questions

- What persistent development-environment fix should replace the temporary
  `PYTHONPATH=src` workaround for macOS hidden editable-install `.pth` files?

## Session log

### 2026-10-03 — Block 1.3 completion

- The owner confirmed the full test suite passes after file-reading implementation.
  Black, Ruff, and mypy also pass.
- Marked Block 1.3 complete and advanced the next action to Block 1.4 lexical
  code-search design. No code-search implementation has been added.

### 2026-10-03 — Block 1.3 implementation

- The owner accepted the result shape and test inventory before implementation.
- Added immutable `ReadFileSuccess(path, content)` and repository-bound
  `ReadFileTool` with a configurable default limit of 256 KiB.
- Implemented resolved containment and regular-file checks, bounded binary
  reading, size validation, NUL rejection, strict UTF-8 decoding, exact line
  endings, caller-path preservation, and specific safe filesystem failures.
- Added the accepted tests, including symlink and parent traversal, unsupported
  contents, exact and exceeded byte limits, actual default-limit cases, bounded
  reads during simulated growth, permission failures, disappearance, directory
  replacement, immutable results, unchanged contents, and unexpected exceptions.
- Reject negative byte limits; a zero limit permits only an empty file.
- Black, Ruff, and full mypy checks pass. Pytest has not been run for Block 1.3;
  the owner will run it. Changes are uncommitted.

### 2026-10-03 — Block 1.3 design begins

- Reviewed the common tool contract and learning workflow. File reading already
  promises exact text, a repository-relative result path, immutable success or
  controlled failure, repository confinement, and no modifications.
- The owner chose strict UTF-8; invalid bytes return `unsupported_content`
  without encoding guesses or replacement characters. Recorded this in the
  Block 1.3 workbook.
- The owner selected 256 KiB (262,144 bytes) as the starting per-file limit.
  Oversized files return `file_too_large` with no partial contents; bounded reads
  inspect at most the limit plus one byte. Remaining contract choices are next.
- The owner agreed to reject NUL-containing content as `unsupported_content`,
  including content that would otherwise decode as UTF-8. This heuristic does
  not claim to detect all binary formats.
- The owner agreed to internal file-symlink access with caller-path preservation,
  rejection of outside targets, `file_not_found` for missing targets, and
  `not_a_file` for directory or special-object targets.
- Proposed immutable success fields and a test inventory in the workbook;
  verification design is next before implementation.
  No file-reading code or tests have been added.

### 2026-10-03 — Block 1.2 completion

- The owner confirmed the full expanded test suite passes, including caller-path
  regression coverage. Black, Ruff, and mypy checks also pass.
- Marked Block 1.2 complete in the roadmap and advanced the next action to the
  Block 1.3 `read_file` design exercise. No file-reading code has been added.

### 2026-10-03 — Caller-path regression coverage

- Added the three agreed cases: ordinary parent traversal preserves the caller
  path; a symlink followed by `..` lists the target's parent while preserving
  the alias; parent traversal through a symlink that resolves outside is rejected.
- The symlink-parent fixture includes a root-only file so an incorrect lexical
  normalization would produce visibly different results.
- Application code already expresses this contract and needed no further edits.
- Black, Ruff, and full mypy checks pass. The owner will run the expanded suite.

### 2026-10-03 — Permission failures, entry limits, and coverage review

- The owner requested a walkthrough of design choices with AI implementation,
  and proposed testing the limit with a large directory.
- Used `os.scandir()` for streaming enumeration with deterministic closure.
  All immediate entries count toward the limit, including hidden entries.
  The first excess entry produces `directory_too_large` without a partial result.
- Added safe `permission_denied` handling for resolution and directory access.
  Specific filesystem exceptions are caught; unexpected defects propagate.
- Added a real 1,001-entry directory test, exact-limit and hidden-entry tests,
  and an instrumented test for stopping and closing after the first excess entry.
- Expanded coverage for permission failures during resolution, opening, and
  iteration; unexpected errors; empty and explicitly hidden directories;
  `.gitignore` independence and unchanged file contents; named pipes; outside
  paths; ordinary invalid paths; and disappearing directories or symlink targets.
- Added a narrow mypy suppression to the existing immutability test because its
  intentional assignment must reach runtime to verify `FrozenInstanceError`.
- Black, Ruff, and full mypy checks pass. The expanded pytest suite has not yet
  been run; the owner ran the earlier 13 focused tests successfully.
- The owner clarified that caller-path preservation was already decided:
  results use the supplied path, while resolution governs access and boundary
  checks. `..` remains in returned paths; the workbook now makes this explicit.
  No new normalization design is required. Shared request-shape validation
  remains assigned to Block 1.5.

### 2026-10-03 — Requested-path symlink failures

- The owner authorized AI-written code for this session.
- Added tests for outside, dangling, and file symlinks used as the requested
  directory. The owner reported 11 passing tests and two expected failures:
  uncaught `FileNotFoundError` and `NotADirectoryError`.
- Wrapped directory iteration to translate those two exceptions into the agreed
  controlled failures. Repository containment remains checked before listing;
  failure messages do not expose absolute filesystem paths.
- Ran Black on both changed Python files and Ruff across the repository; both
  completed successfully. The owner then confirmed all 13 focused `list_files`
  tests pass. Changes are uncommitted.

### 2026-09-26 — Formatting and quality checks

- The owner reported that Black, Ruff, mypy, and pytest all pass.
- Pytest requires the temporary `PYTHONPATH=src` workaround in this checkout;
  the owner confirmed `PYTHONPATH=src uv run pytest` passes with 2 tests.
- Set the next action to designing and adding a failing test for hidden-entry
  behavior; implementation remains incomplete.

### 2026-09-26 — Hidden-entry test design

- The owner added root-level and requested-subdirectory tests for default
  filtering and `include_hidden=True`.
- `PYTHONPATH=src uv run pytest` collected 6 tests: 4 passed and the 2 tests
  checking default hidden-entry exclusion failed because hidden entries are
  still returned. Hidden-entry filtering remains unimplemented.

### 2026-09-26 — Hidden-entry filtering

- Implemented filtering for dot-prefixed entries: they are excluded by default
  and included when `include_hidden=True`.
- Added tests for root and explicitly requested subdirectory listings, covering
  both default filtering and inclusion. Listing remains non-recursive.
- The owner reports all 6 tests pass, along with Black, Ruff, and mypy.
- Next, commit and push the changes. After that, begin the symlink-classification
  exercise by defining its contract and proposing tests before implementation.

### 2026-09-27 — Symlink contract design

- Confirmed that listed symlink entries are classified as `symlink` whether
  they target files, directories, outside paths, or missing paths; entry
  listing does not follow or expose the target.
- Confirmed that an explicitly requested symlink directory may be followed
  only when its resolved target remains inside the declared repository root.
  Outside targets return `outside_repository`.
- Chose to preserve the caller's repository-relative symlink path in result
  directory and entry paths.
- Defined a requested directory or symlink target disappearing before listing
  as `directory_not_found`; a dangling symlink encountered as an entry remains
  a successful symlink listing.
- Updated the Block 1.2 workbook contract and test plan. Next, add the proposed
  tests and observe their initial failures before implementing behavior.

### 2026-09-27 — Shared failure result and symlink tests

- Defined shared `ToolFailure` as an immutable result with `code: str` and
  `message: str`, used alongside tool-specific success results.
- The owner added the shared-result implementation and reported that its
  construction/field and immutability tests pass.
- Added four `list_files` symlink-entry tests in the working tree: links to an
  in-repository file, an in-repository directory, a dangling target, and an
  outside file target. Symlink test outcomes have not yet been reported.
- Next, add tests for symlinks supplied as the requested directory path, then
  run the focused tests and note the expected failures before implementation.

### 2026-09-28 — Symlink classification and output paths

- The owner updated `list_files` to classify symlink entries before checking
  file or directory types and to reject requested paths whose resolved targets
  fall outside the repository root.
- Added an internal directory-symlink test requiring results to preserve the
  caller's alias path. The owner reports the path behavior now works.
- Result entry paths are built from the requested path and child name, while
  the resolved path remains responsible for filesystem access and containment.
- Next, add requested-path tests for outside, dangling, and file symlinks and
  implement the corresponding controlled failure behavior.

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

> Read `AGENTS.md` and `docs/STATUS.md`. Blocks 1.2 and 1.3 are complete; the owner
> confirmed the full test suite passes, and Black, Ruff, and mypy pass. Begin
> Block 1.4 by defining the lexical `search_code` contract and tests.
> Run Black and Ruff before commits. Keep using `PYTHONPATH=src` until the
> macOS editable-install issue has a persistent fix, and update project status
> when we finish.
