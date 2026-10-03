import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

import archagent.tools.list_files as list_files_module
from archagent.tools.list_files import (
    EntryKind,
    ListEntry,
    ListFilesSuccess,
    ListFilesTool,
)
from archagent.tools.results import ToolFailure


def test_list_files_returns_sorted_immediate_entries(tmp_path: Path) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"
    child_directory.mkdir()
    (child_directory / "nested.py").write_text("", encoding="utf-8")

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(
            ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
            ListEntry(path="zebra.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_excludes_hidden_entries_by_default(tmp_path: Path) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")
    (tmp_path / ".hidden_giraffe.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"
    hidden_child_directory = tmp_path / ".beta"
    child_directory.mkdir()
    hidden_child_directory.mkdir()
    (child_directory / "nested.py").write_text("", encoding="utf-8")
    (child_directory / ".hidden_file.py").write_text("", encoding="utf-8")

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(
            ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
            ListEntry(path="zebra.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_includes_hidden_entries(tmp_path: Path) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")
    (tmp_path / ".hidden_giraffe.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"
    hidden_child_directory = tmp_path / ".beta"

    child_directory.mkdir()
    hidden_child_directory.mkdir()

    (child_directory / "nested.py").write_text("", encoding="utf-8")
    (child_directory / ".hidden_file.py").write_text("", encoding="utf-8")

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files(".", include_hidden=True)

    assert result == ListFilesSuccess(
        directory=".",
        entries=(
            ListEntry(path=".beta", kind=EntryKind.DIRECTORY),
            ListEntry(path=".hidden_giraffe.py", kind=EntryKind.FILE),
            ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
            ListEntry(path="zebra.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_excludes_hidden_entries_in_requested_subdirectory_by_default(
    tmp_path: Path,
) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")
    (tmp_path / ".hidden_giraffe.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"

    child_directory.mkdir()

    (child_directory / "nested.py").write_text("", encoding="utf-8")
    (child_directory / ".hidden_file.py").write_text("", encoding="utf-8")

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files("alpha")

    assert result == ListFilesSuccess(
        directory="alpha",
        entries=(ListEntry(path="alpha/nested.py", kind=EntryKind.FILE),),
    )


def test_list_files_includes_hidden_entries_in_requested_subdirectory(
    tmp_path: Path,
) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")
    (tmp_path / ".hidden_giraffe.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"

    child_directory.mkdir()

    (child_directory / "nested.py").write_text("", encoding="utf-8")
    (child_directory / ".hidden_file.py").write_text("", encoding="utf-8")

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files("alpha", include_hidden=True)

    assert result == ListFilesSuccess(
        directory="alpha",
        entries=(
            ListEntry(path="alpha/.hidden_file.py", kind=EntryKind.FILE),
            ListEntry(path="alpha/nested.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_symlink_returns_symlink_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"
    child_directory.mkdir()
    (child_directory / "nested.py").write_text("", encoding="utf-8")

    target = tmp_path / "beta.txt"
    target.write_text("", encoding="utf-8")

    link = tmp_path / "delta.txt"
    link.symlink_to(target)

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(
            ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
            ListEntry(path="beta.txt", kind=EntryKind.FILE),
            ListEntry(path="delta.txt", kind=EntryKind.SYMLINK),
            ListEntry(path="zebra.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_symlink_returns_symlink_directory(
    tmp_path: Path,
) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"
    child_directory.mkdir()
    (child_directory / "nested.py").write_text("", encoding="utf-8")

    target = tmp_path / "beta"
    target.mkdir()

    link = tmp_path / "delta"
    link.symlink_to(target)

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(
            ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
            ListEntry(path="beta", kind=EntryKind.DIRECTORY),
            ListEntry(path="delta", kind=EntryKind.SYMLINK),
            ListEntry(path="zebra.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_symlink_returns_dangling_symlink(
    tmp_path: Path,
) -> None:
    (tmp_path / "zebra.py").write_text("", encoding="utf-8")

    child_directory = tmp_path / "alpha"
    child_directory.mkdir()
    (child_directory / "nested.py").write_text("", encoding="utf-8")

    target = tmp_path / "beta"

    link = tmp_path / "delta"
    link.symlink_to(target)

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(
            ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
            ListEntry(path="delta", kind=EntryKind.SYMLINK),
            ListEntry(path="zebra.py", kind=EntryKind.FILE),
        ),
    )


def test_list_files_lists_outside_target_symlink(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("", encoding="utf-8")

    link = repository / "outside_link.txt"
    link.symlink_to(outside_file)

    tool = ListFilesTool(repository_root=repository)

    result = tool.list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(ListEntry(path="outside_link.txt", kind=EntryKind.SYMLINK),),
    )


def test_list_files_preserves_internal_symlink_path(
    tmp_path: Path,
) -> None:
    target = tmp_path / "actual"
    target.mkdir()
    (target / "file.py").write_text("", encoding="utf-8")

    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)

    tool = ListFilesTool(repository_root=tmp_path)

    result = tool.list_files("alias")

    assert result == ListFilesSuccess(
        directory="alias",
        entries=(ListEntry(path="alias/file.py", kind=EntryKind.FILE),),
    )


def test_list_files_rejects_requested_outside_directory_symlink(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repository / "alias").symlink_to(outside, target_is_directory=True)

    result = ListFilesTool(repository_root=repository).list_files("alias")

    assert isinstance(result, ToolFailure)
    assert result.code == "outside_repository"


def test_list_files_requested_dangling_symlink_returns_directory_not_found(
    tmp_path: Path,
) -> None:
    (tmp_path / "alias").symlink_to(tmp_path / "missing", target_is_directory=True)

    result = ListFilesTool(repository_root=tmp_path).list_files("alias")

    assert isinstance(result, ToolFailure)
    assert result.code == "directory_not_found"


def test_list_files_requested_file_symlink_returns_not_a_directory(
    tmp_path: Path,
) -> None:
    target = tmp_path / "file.py"
    target.write_text("", encoding="utf-8")
    (tmp_path / "alias").symlink_to(target)

    result = ListFilesTool(repository_root=tmp_path).list_files("alias")

    assert isinstance(result, ToolFailure)
    assert result.code == "not_a_directory"


def test_list_files_rejects_large_directory(tmp_path: Path) -> None:
    for index in range(1_001):
        (tmp_path / f"entry_{index}.py").touch()

    result = ListFilesTool(repository_root=tmp_path).list_files(".")

    assert isinstance(result, ToolFailure)
    assert result.code == "directory_too_large"


def test_list_files_accepts_exact_entry_limit(tmp_path: Path) -> None:
    for name in ("c.py", "A.py", "b.py"):
        (tmp_path / name).touch()

    result = ListFilesTool(repository_root=tmp_path, max_entries=3).list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=tuple(
            ListEntry(path=name, kind=EntryKind.FILE)
            for name in ("A.py", "b.py", "c.py")
        ),
    )


@pytest.mark.parametrize("include_hidden", [False, True])
def test_list_files_hidden_entries_count_toward_limit(
    tmp_path: Path,
    include_hidden: bool,
) -> None:
    for index in range(4):
        (tmp_path / f".hidden_{index}").touch()

    result = ListFilesTool(repository_root=tmp_path, max_entries=3).list_files(
        ".",
        include_hidden=include_hidden,
    )

    assert isinstance(result, ToolFailure)
    assert result.code == "directory_too_large"


def test_list_files_stops_scanning_and_closes_iterator_at_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for index in range(10):
        (tmp_path / f"entry_{index}").touch()
    examined: list[str] = []
    closed = False
    original_scandir = os.scandir

    @contextmanager
    def tracked_scan(directory: Path) -> Iterator[Iterator[os.DirEntry[str]]]:
        nonlocal closed
        with original_scandir(directory) as children:

            def tracked_entries() -> Iterator[os.DirEntry[str]]:
                for child in children:
                    examined.append(child.name)
                    yield child

            try:
                yield tracked_entries()
            finally:
                closed = True

    monkeypatch.setattr(list_files_module, "scandir", tracked_scan)

    result = ListFilesTool(repository_root=tmp_path, max_entries=3).list_files(".")

    assert isinstance(result, ToolFailure)
    assert result.code == "directory_too_large"
    assert len(examined) == 4
    assert closed


@pytest.mark.parametrize("stage", ["open", "iteration"])
def test_list_files_permission_failure_returns_safe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    (tmp_path / "file.py").touch()
    original_scandir = os.scandir

    @contextmanager
    def denied_scan(directory: Path) -> Iterator[Iterator[os.DirEntry[str]]]:
        if stage == "open":
            raise PermissionError(f"Access denied: {directory}")

        with original_scandir(directory) as children:

            def denied_entries() -> Iterator[os.DirEntry[str]]:
                yield from children
                raise PermissionError(f"Access denied: {directory}")

            yield denied_entries()

    monkeypatch.setattr(list_files_module, "scandir", denied_scan)

    result = ListFilesTool(repository_root=tmp_path).list_files(".")

    assert isinstance(result, ToolFailure)
    assert result.code == "permission_denied"
    assert str(tmp_path) not in result.message


def test_list_files_permission_failure_during_path_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_resolve = Path.resolve

    def denied_resolve(path: Path, strict: bool = False) -> Path:
        if path.name == "denied":
            raise PermissionError(f"Access denied: {path}")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", denied_resolve)

    result = ListFilesTool(repository_root=tmp_path).list_files("denied")

    assert isinstance(result, ToolFailure)
    assert result.code == "permission_denied"
    assert str(tmp_path) not in result.message


def test_list_files_unexpected_exception_propagates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_scan(directory: Path) -> None:
        raise RuntimeError("Unexpected defect")

    monkeypatch.setattr(list_files_module, "scandir", broken_scan)

    with pytest.raises(RuntimeError, match="Unexpected defect"):
        ListFilesTool(repository_root=tmp_path).list_files(".")


def test_list_files_empty_directory(tmp_path: Path) -> None:
    assert ListFilesTool(repository_root=tmp_path).list_files(".") == ListFilesSuccess(
        directory=".",
        entries=(),
    )


def test_list_files_explicitly_requested_hidden_directory(tmp_path: Path) -> None:
    directory = tmp_path / ".hidden"
    directory.mkdir()
    (directory / "file.py").touch()

    assert ListFilesTool(repository_root=tmp_path).list_files(
        ".hidden"
    ) == ListFilesSuccess(
        directory=".hidden",
        entries=(ListEntry(path=".hidden/file.py", kind=EntryKind.FILE),),
    )


def test_list_files_does_not_apply_gitignore_or_change_contents(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("content\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    result = ListFilesTool(repository_root=tmp_path).list_files(".")

    assert result == ListFilesSuccess(
        directory=".",
        entries=(ListEntry(path="ignored.py", kind=EntryKind.FILE),),
    )
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes unavailable")
def test_list_files_special_entry_is_other(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "pipe")

    assert ListFilesTool(repository_root=tmp_path).list_files(".") == ListFilesSuccess(
        directory=".",
        entries=(ListEntry(path="pipe", kind=EntryKind.OTHER),),
    )


@pytest.mark.parametrize("absolute", [False, True])
def test_list_files_rejects_outside_requested_path(
    tmp_path: Path, absolute: bool
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    requested = str(outside) if absolute else "../outside"

    result = ListFilesTool(repository_root=repository).list_files(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "outside_repository"


@pytest.mark.parametrize(
    ("requested", "expected_code"),
    [("missing", "directory_not_found"), ("file.py", "not_a_directory")],
)
def test_list_files_invalid_directory_returns_failure(
    tmp_path: Path,
    requested: str,
    expected_code: str,
) -> None:
    (tmp_path / "file.py").touch()

    result = ListFilesTool(repository_root=tmp_path).list_files(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == expected_code


@pytest.mark.parametrize("use_symlink", [False, True])
def test_list_files_directory_disappears_before_listing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_symlink: bool,
) -> None:
    directory = tmp_path / "target"
    directory.mkdir()
    requested = "target"
    if use_symlink:
        (tmp_path / "alias").symlink_to(directory, target_is_directory=True)
        requested = "alias"
    original_scandir = os.scandir

    @contextmanager
    def disappearing_scan(path: Path) -> Iterator[Iterator[os.DirEntry[str]]]:
        directory.rmdir()
        with original_scandir(path) as children:
            yield children

    monkeypatch.setattr(list_files_module, "scandir", disappearing_scan)

    result = ListFilesTool(repository_root=tmp_path).list_files(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "directory_not_found"


def test_list_files_preserves_parent_components_in_caller_path(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    (tmp_path / "file.py").touch()

    result = ListFilesTool(repository_root=tmp_path).list_files("folder/..")

    assert result == ListFilesSuccess(
        directory="folder/..",
        entries=(
            ListEntry(path="folder/../file.py", kind=EntryKind.FILE),
            ListEntry(path="folder/../folder", kind=EntryKind.DIRECTORY),
        ),
    )


def test_list_files_symlink_parent_uses_target_parent_and_preserves_alias(
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    (package / "nested").mkdir(parents=True)
    (package / "file.py").touch()
    # A root-only file makes listing the wrong parent observable.
    (tmp_path / "root_only.py").touch()
    (tmp_path / "alias").symlink_to(package / "nested", target_is_directory=True)

    result = ListFilesTool(repository_root=tmp_path).list_files("alias/..")

    assert result == ListFilesSuccess(
        directory="alias/..",
        entries=(
            ListEntry(path="alias/../file.py", kind=EntryKind.FILE),
            ListEntry(path="alias/../nested", kind=EntryKind.DIRECTORY),
        ),
    )


def test_list_files_rejects_parent_escape_after_symlink(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "alias").symlink_to(repository, target_is_directory=True)

    result = ListFilesTool(repository_root=repository).list_files("alias/..")

    assert isinstance(result, ToolFailure)
    assert result.code == "outside_repository"
