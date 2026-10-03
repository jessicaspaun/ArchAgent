# Project Status

Last updated: 2026-10-03

## Current position

- **Phase:** 1 — Tool system, without an LLM
- **Block:** 1.6 — Tool testing (next; review not started)
- **State:** Block 1.5 is complete; all 178 repository tests, Black, Ruff, and mypy pass
- **Application code:** The fixed `ToolRegistry` supports immutable metadata discovery, strict request validation, default filling, unknown-tool recovery, and typed invocation adapters. Separate repository setup validates and retains the resolved boundary, rejects protected-source overlap, and binds all three repository tools.
- **Repository state:** Blocks 1.2–1.4 are committed. Block 1.5 completion includes registry/setup source, 40 tests, and finalized contract documentation.

## Next action

Begin Block 1.6 by reviewing the existing 178 tests as a portfolio: classify
unit, contract, integration, failure, and security coverage; identify meaningful
gaps and unnecessary duplication; use coverage only to locate unexercised code.
Keep code tests distinct from later agent evaluations.

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

### 2026-10-03 — Block 1.5 implementation and completion

- Collaboratively designed registry entries, exact-type validation, tuple
  construction, first-error failures, path constraints, defaults, alphabetical
  discovery, unknown-tool recovery, typed adapters, read-only arguments,
  repository setup, overlap rules, and initialization errors.
- Added `ToolRegistry`, immutable definition/discovery records, a read-only
  lookup, validation and default filling, and typed invocation adapters.
- Added separate repository setup that strictly resolves roots, rejects symmetric
  protected-source overlap, binds all three tools, and constructs their agreed
  public definitions.
- Added 40 registry/setup tests covering definition consistency, immutability,
  discovery privacy, strict validation, defaults, all three real invocations,
  failures, retained resolved roots, overlap, and safe startup errors.
- Focused tests passed on the first behavior run. Mypy exposed annotation gaps
  in metadata construction and test helpers; those were tightened. Review then
  improved strict startup resolution and rejected incompatible or duplicate
  constraints.
- Final verification: `PYTHONPATH=src .venv/bin/pytest -q` reported 178 passed.
  Black, Ruff, and strict mypy pass. Marked Block 1.5 complete.

### 2026-10-03 — Block 1.5 collaborative design begins

- The owner requested working through the registry together after code-search
  completion. Reviewed existing agreements: fixed name-to-definition mapping,
  immutable metadata, metadata-only discovery, validation before invocation,
  duplicate-name rejection, and controlled unknown-tool handling.
- Begin with the owner's proposed entry structure and request flow. No registry
  implementation or tests have been added.
- The owner identified name, description, and path argument metadata; clarified
  that entries also retain the callable and that argument definitions are separate
  from per-request values.
- The owner chose strict validation: incorrect argument types are rejected
  without coercion, and invalid requests must never invoke the callable.
- The owner chose exact built-in type matching so Booleans and integers cannot
  be accepted for one another under Python's subclass rules.
- The owner accepted public metadata for all three tools, including nonempty
  path constraints, empty-query support, optional hidden flags, and no extras.
- The owner accepted symmetric resolved-path overlap rejection: a target cannot
  equal, contain, or sit inside the protected ArchAgent source tree. Separate
  non-overlapping clones remain allowed.
- After reviewing `Callable`, the owner chose uniform typed adapters. Each
  adapter accepts validated arguments and makes an explicitly typed tool call;
  the registry avoids a broad `Callable[..., ToolResult]` boundary.
- The owner chose a read-only validated/default-filled argument mapping for
  adapters. Added the proposed registry and repository-setup test inventory.
- The owner accepted `target_permission_denied` and
  `invalid_protected_source_root`; unexpected setup defects propagate.
- The owner chose `invalid_tool_definition` for inconsistent or unsupported
  registry metadata. The contract is now ready for verification-plan review.
- The owner proposed tuple input for construction so duplicate tool definitions
  remain visible before the name lookup mapping is created.
- The owner chose first-error validation reporting using `invalid_arguments` and
  a safe message in `ToolFailure`. Unknown names retain `unknown_tool`.
- The owner chose nonempty constraints specifically for path arguments, keeping
  empty search queries valid. Repository-relative paths remain required by the
  common contract; filesystem safety checks remain with the tools.
- The owner chose a separate repository setup function to validate the target,
  retain its resolved root, bind the tools, and build the generic registry.
- The owner chose a dedicated initialization exception carrying a stable code
  and safe message. Runtime request failures remain `ToolFailure` results.
- The owner accepted `target_not_found`, `target_not_a_directory`,
  `target_overlaps_archagent`, and `duplicate_tool_name` as startup codes.
- The owner chose registry-owned default filling before invocation. Argument
  metadata must distinguish no default from values such as `False` or `None`.
- The owner chose alphabetical discovery with immutable serializable metadata.
  Callables, repository roots, and internal validation functions stay private.
- The owner chose an `unknown_tool` message containing the requested name and
  alphabetically ordered available names, without invoking a callable.

### 2026-10-03 — Block 1.4 implementation and completion

- The owner authorized finishing code search without further participation,
  including remaining routine contract choices, implementation, and verification.
- Implemented recursive literal, case-sensitive search with hidden entries
  excluded by default, optional inclusion, and no `.gitignore` interpretation.
- Added immutable match, skip, and success records. Results use one-based line
  numbers, preserve line whitespace and caller aliases, and report explicit
  truncation only after another matching line is discovered.
- Reused listing and reading tools with an explicit traversal stack. Each listing
  receives the remaining global entry budget; hidden entries and links count
  before filtering. Unsupported/oversized files and special objects are reported
  as skips. Access failures return controlled failures without partial matches.
- Added 55 search tests. The initial run found a case-insensitive filesystem
  fixture collision; corrected the filenames. The full suite then passed:
  `PYTHONPATH=src .venv/bin/pytest -q` reported 138 passed.
- Black, Ruff, and strict mypy pass. Marked Block 1.4 complete and set Block 1.5
  registry design as the next action. No registry implementation was added.

### 2026-10-03 — Block 1.4 design begins

- Reviewed existing search requirements: lexical search, read-only repository
  access, and the common tool contract. Detailed search behavior is still open.
- Started with query semantics and case handling. No code-search implementation
  or tests have been added.
- The owner chose grep-style behavior implemented in Python. Matching lines
  should be reported with structured file paths, line numbers, and text.
  Literal case-sensitive matching and recursive directory scope are proposed.
- The owner agreed to recursive search under a required repository-relative
  directory path, using `"."` for the repository root. Symlink traversal is next.
- The owner agreed to skip discovered symlinks. Explicitly requested internal
  directory symlinks may be followed with caller-path preservation; outside
  requested targets are rejected. Unsupported/oversized-file handling is next.
- The owner accepted skipping unsupported and oversized files with explicit
  paths and reasons, while permission failures or disappearing files stop the
  search with a controlled failure and no partial matches.
- The owner chose bounded partial results with `truncated=True` when the match
  limit is exceeded. Match-cap and traversal-budget values are next.
- The owner accepted starting limits of 100 matching lines and 1,000 examined
  entries, with controlled `search_too_large` for traversal-budget overflow.
- Added proposed exact result fields, visibility rules, and a test inventory for
  final review. Matching semantics remain explicitly proposed pending review.

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

> Read `AGENTS.md` and `docs/STATUS.md`. Blocks 1.2 through 1.5 are complete.
> All 178 repository tests, Black, Ruff, and mypy pass. Begin Block 1.6 by
> reviewing and classifying the test portfolio, then identify meaningful gaps
> and duplication before adding or changing tests.
> Run Black and Ruff before commits. Keep using `PYTHONPATH=src` until the
> macOS editable-install issue has a persistent fix, and update project status
> when we finish.
