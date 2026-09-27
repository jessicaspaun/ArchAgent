from pathlib import Path

from archagent.tools.list_files import (
    EntryKind,
    ListEntry,
    ListFilesSuccess,
    ListFilesTool,
)


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
