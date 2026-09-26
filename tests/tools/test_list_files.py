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
