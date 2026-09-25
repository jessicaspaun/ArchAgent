# Phase 1 Workbook

Phase 1 builds and tests the deterministic repository-tool system without an
LLM. The goal is to make the mechanics, trust boundaries, and failure behavior
visible before they are used by an agent loop.

## 1.1 Common tool contract

### Repository boundary

A repository-tool collection is created for one user-selected target repository
directory. It resolves and retains that directory as an immutable access
boundary for the life of the run. The target repository root is configuration
owned by the application; it is not an argument that a model or individual tool
call may replace.

Every filesystem operation accepts repository-relative input. Before accessing
a path, the repository tool resolves its final location and verifies that it is
inside the authorized target repository. Inputs that escape through an absolute
path, `..`, or a symbolic link are rejected. This safety check belongs to the
repository-tool layer even when another layer has already validated the shape of
the request.

The V0.1 repository tools may only list files, read text files, and perform
lexical searches. They do not create, modify, delete, rename, or execute
repository files. This is an application-level capability boundary: V0.1 does
not yet claim to be an operating-system sandbox.

ArchAgent must not review the source checkout from which it is currently
running. Startup rejects any target directory whose resolved directory tree
overlaps the protected ArchAgent application source root. A separate clone at a
non-overlapping path is allowed. The protected source root is explicitly
identified by application startup; it is not inferred from the shell's current
working directory.

The exact policy for symbolic links whose source and final destination are both
inside the target repository is deferred to the `list_files` and `read_file`
design exercises.

### Tool definition

Every tool has a stable, machine-friendly name, a specific description, a
machine-checkable argument contract, and a Python callable. Names use a stable
form such as `read_file`, `list_files`, and `search_code`.

The model-facing description must say what the tool does using operational
language. For example:

```text
Name: read_file
Description: Reads the text contents of one file within the configured
repository without modifying the file.
```

The model may eventually receive the name, description, and argument contract.
The Python callable, bound repository root, validation implementation, and
registry remain under harness control. The model proposes a tool name and
arguments; it never receives or directly executes the callable.

### Argument contract

Each tool argument is described by a small immutable Python dataclass containing
at least:

- its name;
- its expected type;
- whether it is required; and
- its description.

The tool definition also states whether extra arguments are allowed. V0.1 tools
reject extra arguments unless the individual definition explicitly permits
them.

For `read_file`, the initial argument contract is:

```text
Name: path
Type: string
Required: yes
Description: A repository-relative path to an existing file.
Extra arguments allowed: no
```

The invocation layer validates request shape: whether the tool exists, required
arguments are present, argument values have the declared types, and unexpected
arguments are absent. The repository tool validates operation semantics and
safety: whether the path stays inside the target repository, exists, has the
required file type, and can be read.

### Success and failure results

Expected operations return one of two distinct immutable result types rather
than one object containing optional success and error fields:

```text
Operation-specific success
OR
ToolFailure
```

This makes a result containing both an observation and an error unrepresentable.
An internal `ok` Boolean is unnecessary because the result type identifies the
outcome. A later model-facing serialization may add `ok: true` or `ok: false` if
that is useful, but that representation is a Phase 2 decision.

For `read_file`, a successful observation contains the normalized
repository-relative path and the exact text contents. An empty file has valid
contents represented by the empty string `""`, not `None`.

A controlled failure contains a stable machine-readable error code and a safe,
readable message. It contains no success observation. Relevant error context
uses repository-relative paths rather than machine-specific absolute paths.

Initial controlled tool errors include:

| Code | Meaning |
| --- | --- |
| `file_not_found` | The requested file does not exist. |
| `outside_repository` | The resolved path is outside the authorized target repository. |
| `permission_denied` | The operating system refused access. |
| `not_a_file` | A read request points to a directory or another non-file object. |
| `unsupported_content` | The requested file cannot be read as supported text. |
| `unknown_tool` | No registered tool has the requested name. |

Initialization failures are separate from tool-operation failures. They occur
before a tool is invoked and stop the run from starting. The startup error
`target_overlaps_archagent` tells the user to provide a target directory that
does not overlap ArchAgent's application source directory. A missing target,
target that is not a directory, and duplicate tool names are also initialization
failures, although their final error codes will be chosen with their
implementations.

### Error ownership and visibility

Known repository and input conditions are part of the tool contract and become
specific controlled failures. A tool catches an exception only when it
understands the condition and can translate it accurately. It must not catch all
exceptions and disguise programming defects as ordinary repository failures.

Unexpected defects may propagate to the harness's outer safety boundary. The
harness will eventually return a generic `internal_error` rather than crashing
the CLI. Detailed exception types, tracebacks, and necessary absolute paths stay
in internal logs. Expected failures generally require no traceback. Logs must
also avoid credentials and unnecessary repository contents.

In Phase 1 there is no harness or model call. Tests therefore exercise the tool
contract directly; the outer conversion of unexpected exceptions into a safe
harness failure will be implemented and tested in the agent-loop phase.

### Tool registry

The registry is a mapping from each stable tool name to its tool definition. It
supports discovery and invocation without a growing `if`/`elif` chain.

Registry construction rejects duplicate names instead of silently replacing a
tool. Once a run begins, its registry is fixed: tools cannot be added, removed,
or replaced by the model or other runtime input. A request for a name absent
from the registry returns `unknown_tool` and may include the requested name and
the available tool names so the caller can recover.

The registry's internal entry contains the description, argument contract, and
callable. Discovery exposes only the serializable name, description, and
argument contract. Invocation finds the registered entry, validates raw
arguments, and only then calls the retained Python callable.

### Contract test inventory

The contract will be demonstrated with deterministic code tests, not agent
evaluations. Most tests will use temporary repository directories.

Construction and configuration:

1. An existing directory can become the resolved target repository root.
2. A missing target path produces a controlled initialization failure.
3. A target path that is a file produces a controlled initialization failure.
4. The bound target root cannot be replaced after construction.
5. A target that overlaps the protected ArchAgent source root is rejected.
6. A separate, non-overlapping clone is allowed.
7. Duplicate registry names are rejected during registry construction.
8. The registry cannot be changed during a run.

Successful operations:

1. Reading an in-repository text file returns its normalized relative path and
   exact contents.
2. Reading an empty file returns `""` as its contents.
3. Listing an in-repository directory returns the entries required by the
   `list_files` contract.
4. Searching for known text returns the matches required by the `search_code`
   contract.

Request validation and security:

1. Missing, incorrectly typed, and unexpected arguments are rejected before the
   callable runs.
2. An unknown tool name returns `unknown_tool` and does not invoke a callable.
3. A `..` path that escapes the repository is rejected.
4. An absolute path outside the repository is rejected.
5. A symlink whose final destination is outside the repository is rejected.
6. No operation for writing, deleting, renaming, or executing files is exposed.

Controlled failures and unexpected state:

1. A missing file returns `file_not_found` rather than an uncontrolled
   traceback.
2. Reading a directory as a file returns `not_a_file`.
3. An operating-system permission failure returns `permission_denied`.
4. Unsupported text content produces `unsupported_content` according to the
   policy defined during `read_file` design.
5. A file that disappears between discovery and access produces an accurate
   controlled failure.
6. An unexpected programming exception is not mislabeled as an expected tool
   error.

Read-only tests compare repository contents before and after tool operations and
verify that no content was changed. They do not promise that filesystem access
metadata is unchanged, because some operating systems may update access times
when a file is read.

Coverage will be used to find unexercised implementation paths, including error
branches. Coverage percentage is not treated as proof that the contract or its
security properties are correct.

### Operational definitions

- **Immutable:** cannot be replaced after construction for the lifetime of the
  run.
- **Resolved path:** the final filesystem location after making the path
  absolute and processing components such as `.` and `..` and any symbolic
  links.
- **Normalized repository-relative path:** a stable path expressed from the
  target repository root without machine-specific parent directories or
  unnecessary path components.
- **Controlled error:** an anticipated failure represented by a stable code and
  safe message rather than an uncontrolled traceback.
- **Startup or initialization error:** a recognized problem that prevents a run
  from being constructed before any tool or model call occurs.
- **Unexpected defect:** a programming error or unclassified failure that is not
  falsely presented as a known repository condition.

