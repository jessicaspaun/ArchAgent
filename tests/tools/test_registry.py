import json
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from types import MappingProxyType

import pytest

from archagent.tools.list_files import ListFilesSuccess
from archagent.tools.read_file import ReadFileSuccess
from archagent.tools.registry import (
    NO_DEFAULT,
    ArgumentConstraint,
    ArgumentDefinition,
    ArgumentMetadata,
    ArgumentType,
    InitializationError,
    OptionalArgumentMetadata,
    ToolAdapter,
    ToolDefinition,
    ToolMetadata,
    ToolRegistry,
    create_repository_registry,
)
from archagent.tools.results import ToolFailure
from archagent.tools.search_code import SearchCodeSuccess, SearchMatch


def failure_adapter(arguments: Mapping[str, object]) -> ToolFailure:
    return ToolFailure(code="called", message=str(dict(arguments)))


def required_path() -> ArgumentDefinition:
    return ArgumentDefinition(
        name="path",
        argument_type=ArgumentType.STRING,
        required=True,
        description="A repository-relative path.",
        constraints=(
            ArgumentConstraint.NONEMPTY,
            ArgumentConstraint.REPOSITORY_RELATIVE,
        ),
    )


def definition(
    name: str = "sample",
    arguments: tuple[ArgumentDefinition, ...] | None = None,
    adapter: ToolAdapter = failure_adapter,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="A sample tool.",
        arguments=(required_path(),) if arguments is None else arguments,
        allow_extra_arguments=False,
        adapter=adapter,
    )


def assert_initialization_code(code: str, action) -> InitializationError:  # type: ignore[no-untyped-def]
    with pytest.raises(InitializationError) as captured:
        action()
    assert captured.value.code == code
    return captured.value


def test_registry_sorts_unique_definitions_and_rejects_duplicate_names() -> None:
    registry = ToolRegistry((definition("zeta"), definition("alpha")))

    assert tuple(tool.name for tool in registry.discover()) == ("alpha", "zeta")

    error = assert_initialization_code(
        "duplicate_tool_name",
        lambda: ToolRegistry((definition("same"), definition("same"))),
    )
    assert "same" in error.message


@pytest.mark.parametrize(
    "bad_definition",
    [
        definition(name=""),
        ToolDefinition("tool", "", (), False, failure_adapter),
        definition(arguments=(required_path(), required_path())),
        definition(
            arguments=(
                ArgumentDefinition(
                    "path",
                    ArgumentType.STRING,
                    True,
                    "Path.",
                    default=".",
                ),
            )
        ),
        definition(
            arguments=(
                ArgumentDefinition(
                    "hidden",
                    ArgumentType.BOOLEAN,
                    False,
                    "Hidden.",
                    default=False,
                    constraints=(ArgumentConstraint.NONEMPTY,),
                ),
            )
        ),
        definition(
            arguments=(
                ArgumentDefinition(
                    "path",
                    ArgumentType.STRING,
                    True,
                    "Path.",
                    constraints=(
                        ArgumentConstraint.NONEMPTY,
                        ArgumentConstraint.NONEMPTY,
                    ),
                ),
            )
        ),
        definition(
            arguments=(
                ArgumentDefinition(
                    "hidden",
                    ArgumentType.BOOLEAN,
                    False,
                    "Hidden.",
                ),
            )
        ),
        definition(
            arguments=(
                ArgumentDefinition(
                    "hidden",
                    ArgumentType.BOOLEAN,
                    False,
                    "Hidden.",
                    default="no",
                ),
            )
        ),
        definition(
            arguments=(
                ArgumentDefinition(
                    "path",
                    ArgumentType.STRING,
                    False,
                    "Path.",
                    default="",
                    constraints=(ArgumentConstraint.NONEMPTY,),
                ),
            )
        ),
    ],
)
def test_registry_rejects_invalid_tool_definitions(
    bad_definition: ToolDefinition,
) -> None:
    assert_initialization_code(
        "invalid_tool_definition", lambda: ToolRegistry((bad_definition,))
    )


def test_registry_and_definition_structures_are_immutable() -> None:
    argument = required_path()
    tool = definition(arguments=(argument,))
    registry = ToolRegistry((tool,))

    with pytest.raises(FrozenInstanceError):
        argument.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        tool.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        registry._definitions = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        registry._lookup["other"] = tool  # type: ignore[index]


def test_adapter_receives_read_only_default_filled_arguments() -> None:
    captured: list[Mapping[str, object]] = []

    def adapter(arguments: Mapping[str, object]) -> ToolFailure:
        captured.append(arguments)
        with pytest.raises(TypeError):
            arguments["include_hidden"] = True  # type: ignore[index]
        return ToolFailure("done", "done")

    hidden = ArgumentDefinition(
        "include_hidden",
        ArgumentType.BOOLEAN,
        False,
        "Include hidden entries.",
        default=False,
    )
    registry = ToolRegistry(
        (definition(arguments=(required_path(), hidden), adapter=adapter),)
    )

    result = registry.invoke("sample", {"path": "."})

    assert result == ToolFailure("done", "done")
    assert len(captured) == 1
    assert isinstance(captured[0], MappingProxyType)
    assert dict(captured[0]) == {"path": ".", "include_hidden": False}


def test_discovery_is_alphabetical_immutable_and_contains_only_metadata() -> None:
    optional = ArgumentDefinition(
        "include_hidden",
        ArgumentType.BOOLEAN,
        False,
        "Include hidden entries.",
        default=False,
    )
    registry = ToolRegistry(
        (
            definition("zeta", arguments=(required_path(), optional)),
            definition("alpha", arguments=()),
        )
    )

    discovered = registry.discover()

    assert discovered == (
        ToolMetadata("alpha", "A sample tool.", (), False),
        ToolMetadata(
            "zeta",
            "A sample tool.",
            (
                ArgumentMetadata(
                    "path",
                    "string",
                    True,
                    "A repository-relative path.",
                    ("nonempty", "repository_relative"),
                ),
                OptionalArgumentMetadata(
                    "include_hidden",
                    "boolean",
                    False,
                    "Include hidden entries.",
                    (),
                    False,
                ),
            ),
            False,
        ),
    )
    serialized = [asdict(tool) for tool in discovered]
    json.dumps(serialized)
    assert "adapter" not in repr(serialized)
    assert "repository_root" not in repr(serialized)
    assert "default" not in serialized[0].get("arguments", {})
    with pytest.raises(FrozenInstanceError):
        discovered[0].name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "Missing required argument 'path'."),
        ({"path": 42}, "Argument 'path' must be a string."),
        ({"path": True}, "Argument 'path' must be a string."),
        ({"path": ""}, "Argument 'path' must not be empty."),
        ({"path": "bad\x00path"}, "Argument 'path' must not contain NUL characters."),
        ({"path": "/outside"}, "Argument 'path' must be repository-relative."),
        ({"path": ".", "zeta": 1, "alpha": 2}, "Unexpected argument 'alpha'."),
    ],
)
def test_invalid_requests_return_first_error_without_invocation(
    arguments: dict[str, object],
    message: str,
) -> None:
    called = False

    def adapter(validated: Mapping[str, object]) -> ToolFailure:
        nonlocal called
        called = True
        return ToolFailure("called", "called")

    registry = ToolRegistry((definition(adapter=adapter),))

    assert registry.invoke("sample", arguments) == ToolFailure(
        "invalid_arguments", message
    )
    assert not called


@pytest.mark.parametrize("value", [1, "false", None])
def test_boolean_arguments_use_exact_type(value: object) -> None:
    hidden = ArgumentDefinition(
        "include_hidden",
        ArgumentType.BOOLEAN,
        False,
        "Include hidden entries.",
        default=False,
    )
    registry = ToolRegistry((definition(arguments=(hidden,)),))

    result = registry.invoke("sample", {"include_hidden": value})

    assert isinstance(result, ToolFailure)
    assert result.code == "invalid_arguments"


def test_empty_non_path_string_remains_valid() -> None:
    query = ArgumentDefinition(
        "query",
        ArgumentType.STRING,
        True,
        "Literal query.",
    )
    registry = ToolRegistry((definition(arguments=(query,)),))

    result = registry.invoke("sample", {"query": ""})

    assert isinstance(result, ToolFailure)
    assert result.code == "called"


def test_unknown_tool_lists_available_names_without_invocation() -> None:
    called = False

    def adapter(arguments: Mapping[str, object]) -> ToolFailure:
        nonlocal called
        called = True
        return ToolFailure("called", "called")

    registry = ToolRegistry(
        (definition("zeta", adapter=adapter), definition("alpha", adapter=adapter))
    )

    result = registry.invoke("missing", {})

    assert result == ToolFailure(
        "unknown_tool",
        "Unknown tool 'missing'. Available tools: alpha, zeta.",
    )
    assert not called


def test_controlled_failures_pass_through_and_unexpected_defects_propagate() -> None:
    failure = ToolFailure("expected", "Expected failure.")
    registry = ToolRegistry((definition(adapter=lambda arguments: failure),))
    assert registry.invoke("sample", {"path": "."}) is failure

    def broken(arguments: Mapping[str, object]) -> ToolFailure:
        raise RuntimeError("Unexpected defect")

    broken_registry = ToolRegistry((definition(adapter=broken),))
    with pytest.raises(RuntimeError, match="Unexpected defect"):
        broken_registry.invoke("sample", {"path": "."})


def make_setup_paths(tmp_path: Path) -> tuple[Path, Path]:
    target = tmp_path / "target"
    protected = tmp_path / "protected"
    target.mkdir()
    protected.mkdir()
    return target, protected


def test_repository_setup_exposes_exact_public_tool_metadata(tmp_path: Path) -> None:
    target, protected = make_setup_paths(tmp_path)

    discovered = create_repository_registry(target, protected).discover()

    assert tuple(item.name for item in discovered) == (
        "list_files",
        "read_file",
        "search_code",
    )
    by_name = {item.name: item for item in discovered}
    assert tuple(arg.name for arg in by_name["list_files"].arguments) == (
        "path",
        "include_hidden",
    )
    assert tuple(arg.name for arg in by_name["read_file"].arguments) == ("path",)
    assert tuple(arg.name for arg in by_name["search_code"].arguments) == (
        "path",
        "query",
        "include_hidden",
    )
    assert all(not item.allow_extra_arguments for item in discovered)


def test_repository_registry_invokes_all_three_tools_and_fills_defaults(
    tmp_path: Path,
) -> None:
    target, protected = make_setup_paths(tmp_path)
    (target / "file.py").write_text("auth\n", encoding="utf-8")
    (target / ".hidden.py").write_text("auth\n", encoding="utf-8")
    registry = create_repository_registry(target, protected)

    listing = registry.invoke("list_files", {"path": "."})
    reading = registry.invoke("read_file", {"path": "file.py"})
    search = registry.invoke("search_code", {"path": ".", "query": "auth"})

    assert isinstance(listing, ListFilesSuccess)
    assert tuple(entry.path for entry in listing.entries) == ("file.py",)
    assert reading == ReadFileSuccess("file.py", "auth\n")
    assert search == SearchCodeSuccess(
        ".",
        "auth",
        (SearchMatch("file.py", 1, "auth"),),
        (),
        False,
    )


def test_repository_setup_resolves_and_retains_target_alias(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    protected = tmp_path / "protected"
    actual.mkdir()
    protected.mkdir()
    (actual / "file.py").write_text("content", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)

    registry = create_repository_registry(alias, protected)
    alias.unlink()

    assert registry.invoke("read_file", {"path": "file.py"}) == ReadFileSuccess(
        "file.py",
        "content",
    )


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_repository_setup_rejects_invalid_targets(tmp_path: Path, kind: str) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()
    target = tmp_path / "target"
    if kind == "file":
        target.touch()

    expected = "target_not_found" if kind == "missing" else "target_not_a_directory"
    error = assert_initialization_code(
        expected, lambda: create_repository_registry(target, protected)
    )
    assert str(tmp_path) not in error.message


@pytest.mark.parametrize("relationship", ["equal", "target_inside", "target_contains"])
def test_repository_setup_rejects_protected_source_overlap(
    tmp_path: Path,
    relationship: str,
) -> None:
    if relationship == "equal":
        target = protected = tmp_path
    elif relationship == "target_inside":
        protected = tmp_path
        target = tmp_path / "target"
        target.mkdir()
    else:
        target = tmp_path
        protected = tmp_path / "protected"
        protected.mkdir()

    error = assert_initialization_code(
        "target_overlaps_archagent",
        lambda: create_repository_registry(target, protected),
    )
    assert str(tmp_path) not in error.message


def test_repository_setup_allows_separate_clone_path(tmp_path: Path) -> None:
    target, protected = make_setup_paths(tmp_path)
    (target / "same.py").write_text("same", encoding="utf-8")
    (protected / "same.py").write_text("same", encoding="utf-8")

    registry = create_repository_registry(target, protected)

    assert registry.invoke("read_file", {"path": "same.py"}) == ReadFileSuccess(
        "same.py",
        "same",
    )


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_repository_setup_rejects_invalid_protected_root(
    tmp_path: Path,
    kind: str,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    protected = tmp_path / "protected"
    if kind == "file":
        protected.touch()

    error = assert_initialization_code(
        "invalid_protected_source_root",
        lambda: create_repository_registry(target, protected),
    )
    assert str(tmp_path) not in error.message


def test_repository_setup_maps_target_permission_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, protected = make_setup_paths(tmp_path)
    original_resolve = Path.resolve

    def denied_resolve(path: Path, strict: bool = False) -> Path:
        if path == target:
            raise PermissionError(f"Denied: {path}")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", denied_resolve)

    error = assert_initialization_code(
        "target_permission_denied",
        lambda: create_repository_registry(target, protected),
    )
    assert str(tmp_path) not in error.message


def test_repository_setup_maps_protected_root_permission_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, protected = make_setup_paths(tmp_path)
    original_resolve = Path.resolve

    def denied_resolve(path: Path, strict: bool = False) -> Path:
        if path == protected:
            raise PermissionError(f"Denied: {path}")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", denied_resolve)

    error = assert_initialization_code(
        "invalid_protected_source_root",
        lambda: create_repository_registry(target, protected),
    )
    assert str(tmp_path) not in error.message


def test_repository_setup_does_not_disguise_unexpected_defect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, protected = make_setup_paths(tmp_path)

    def broken_resolve(path: Path, strict: bool = False) -> Path:
        raise RuntimeError("Unexpected defect")

    monkeypatch.setattr(Path, "resolve", broken_resolve)

    with pytest.raises(RuntimeError, match="Unexpected defect"):
        create_repository_registry(target, protected)


def test_no_default_sentinel_is_distinct_from_none() -> None:
    assert NO_DEFAULT is not None
