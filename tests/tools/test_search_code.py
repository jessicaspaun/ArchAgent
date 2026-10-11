import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from archagent.tools.list_files import (
    EntryKind,
    ListEntry,
    ListFilesSuccess,
    ListFilesTool,
)
from archagent.tools.read_file import ReadFileSuccess, ReadFileTool
from archagent.tools.results import ToolFailure
from archagent.tools.search_code import (
    SearchCodeSuccess,
    SearchCodeTool,
    SearchMatch,
    SkippedFile,
)


def write_text(root: Path, name: str, content: str) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content.encode("utf-8"))


def test_search_code_returns_recursive_matches_in_path_and_line_order(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, "z.py", "auth\n")
    write_text(tmp_path, "a/inside.py", "no match\nauth twice auth\nauth again\n")
    write_text(tmp_path, "a.py", "authentication\n")
    write_text(tmp_path, "B.py", "auth\n")

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert result == SearchCodeSuccess(
        directory=".",
        query="auth",
        matches=(
            SearchMatch("B.py", 1, "auth"),
            SearchMatch("a.py", 1, "authentication"),
            SearchMatch("a/inside.py", 2, "auth twice auth"),
            SearchMatch("a/inside.py", 3, "auth again"),
            SearchMatch("z.py", 1, "auth"),
        ),
        skipped=(),
        truncated=False,
    )


def test_search_code_scopes_to_requested_directory(tmp_path: Path) -> None:
    write_text(tmp_path, "root.py", "auth\n")
    write_text(tmp_path, "src/file.py", "auth\n")
    write_text(tmp_path, "src/nested/file.py", "auth\n")

    result = SearchCodeTool(tmp_path).search_code("./src//", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.directory == "src"
    assert tuple(match.path for match in result.matches) == (
        "src/file.py",
        "src/nested/file.py",
    )


def test_search_code_literal_and_case_sensitive(tmp_path: Path) -> None:
    write_text(tmp_path, "file.py", "a.b\naxb\nA.B\n  a.b a.b  \n")

    result = SearchCodeTool(tmp_path).search_code(".", "a.b")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (
        SearchMatch("file.py", 1, "a.b"),
        SearchMatch("file.py", 4, "  a.b a.b  "),
    )


def test_search_code_preserves_unicode_and_uses_physical_line_endings(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, "file.py", "café\r\ncafé\rcafé\ncafé\u2028inside\n")

    result = SearchCodeTool(tmp_path).search_code(".", "café")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (
        SearchMatch("file.py", 1, "café"),
        SearchMatch("file.py", 2, "café"),
        SearchMatch("file.py", 3, "café"),
        SearchMatch("file.py", 4, "café\u2028inside"),
    )


@pytest.mark.parametrize("create_file", [False, True])
def test_search_code_no_matches_is_success(tmp_path: Path, create_file: bool) -> None:
    if create_file:
        write_text(tmp_path, "file.py", "unrelated\n")

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert result == SearchCodeSuccess(".", "auth", (), (), False)


def test_search_code_empty_file_has_no_lines(tmp_path: Path) -> None:
    write_text(tmp_path, "file.py", "")

    assert SearchCodeTool(tmp_path).search_code(".", "") == SearchCodeSuccess(
        ".",
        "",
        (),
        (),
        False,
    )


def test_search_code_empty_literal_query_matches_each_existing_line(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, "file.py", "one\n\n")

    result = SearchCodeTool(tmp_path).search_code(".", "")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (
        SearchMatch("file.py", 1, "one"),
        SearchMatch("file.py", 2, ""),
    )


def test_search_code_multiline_literal_does_not_match_one_line(tmp_path: Path) -> None:
    write_text(tmp_path, "file.py", "auth\nnext\n")

    result = SearchCodeTool(tmp_path).search_code(".", "auth\nnext")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == ()


@pytest.mark.parametrize("include_hidden", [False, True])
def test_search_code_hidden_files_and_directories(
    tmp_path: Path, include_hidden: bool
) -> None:
    write_text(tmp_path, "visible.py", "auth\n")
    write_text(tmp_path, ".hidden.py", "auth\n")
    write_text(tmp_path, ".hidden/inside.py", "auth\n")
    write_text(tmp_path, "src/.hidden.py", "auth\n")

    result = SearchCodeTool(tmp_path).search_code(
        ".", "auth", include_hidden=include_hidden
    )

    assert isinstance(result, SearchCodeSuccess)
    expected = (
        (".hidden.py", ".hidden/inside.py", "src/.hidden.py", "visible.py")
        if include_hidden
        else ("visible.py",)
    )
    assert tuple(match.path for match in result.matches) == expected
    assert result.skipped == ()


def test_search_code_explicit_hidden_directory_can_be_searched(tmp_path: Path) -> None:
    write_text(tmp_path, ".hidden/file.py", "auth\n")

    result = SearchCodeTool(tmp_path).search_code(".hidden", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (SearchMatch(".hidden/file.py", 1, "auth"),)


def test_search_code_does_not_apply_gitignore_or_modify_contents(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, ".gitignore", "ignored.py\n")
    write_text(tmp_path, "ignored.py", "auth\n")
    before = {file.name: file.read_bytes() for file in tmp_path.iterdir()}

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (SearchMatch("ignored.py", 1, "auth"),)
    assert {file.name: file.read_bytes() for file in tmp_path.iterdir()} == before


def test_search_code_skips_discovered_symlinks_and_cycles(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_text(repository, "actual/file.py", "auth\n")
    write_text(tmp_path, "outside.py", "auth\n")
    (repository / "file_alias").symlink_to(repository / "actual/file.py")
    (repository / "dir_alias").symlink_to(
        repository / "actual", target_is_directory=True
    )
    (repository / "outside").symlink_to(tmp_path / "outside.py")
    (repository / "missing").symlink_to(repository / "missing_target")
    (repository / "actual/cycle").symlink_to(repository, target_is_directory=True)

    result = SearchCodeTool(repository).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (SearchMatch("actual/file.py", 1, "auth"),)
    assert result.skipped == ()


@pytest.mark.parametrize("requested", ["alias", "alias/..", "actual/../actual"])
def test_search_code_explicit_alias_and_parent_paths_are_preserved(
    tmp_path: Path, requested: str
) -> None:
    write_text(tmp_path, "actual/file.py", "auth\n")
    (tmp_path / "actual/nested").mkdir()
    alias_target = (
        tmp_path / "actual/nested" if requested == "alias/.." else tmp_path / "actual"
    )
    (tmp_path / "alias").symlink_to(alias_target, target_is_directory=True)

    result = SearchCodeTool(tmp_path).search_code(requested, "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.directory == requested
    assert result.matches == (SearchMatch(f"{requested}/file.py", 1, "auth"),)


@pytest.mark.parametrize("kind", ["absolute", "parent", "symlink", "symlink_parent"])
def test_search_code_rejects_outside_scope_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_text(tmp_path, "outside/file.py", "auth\n")
    if kind == "absolute":
        requested = str(tmp_path / "outside")
    elif kind == "parent":
        requested = "../outside"
    elif kind == "symlink":
        (repository / "alias").symlink_to(
            tmp_path / "outside", target_is_directory=True
        )
        requested = "alias"
    else:
        (repository / "alias").symlink_to(repository, target_is_directory=True)
        requested = "alias/../outside"

    def forbidden_read(tool: ReadFileTool, path: str) -> ReadFileSuccess | ToolFailure:
        pytest.fail("Outside search scope must not reach file reading")

    monkeypatch.setattr(ReadFileTool, "read_file", forbidden_read)

    result = SearchCodeTool(repository).search_code(requested, "auth")

    assert isinstance(result, ToolFailure)
    assert result.code == "outside_repository"


@pytest.mark.parametrize(
    ("requested", "code"),
    [
        ("missing", "directory_not_found"),
        ("file.py", "not_a_directory"),
        ("dangling", "directory_not_found"),
    ],
)
def test_search_code_invalid_scope_returns_controlled_failure(
    tmp_path: Path, requested: str, code: str
) -> None:
    write_text(tmp_path, "file.py", "auth\n")
    (tmp_path / "dangling").symlink_to(tmp_path / "missing", target_is_directory=True)

    result = SearchCodeTool(tmp_path).search_code(requested, "auth")

    assert isinstance(result, ToolFailure)
    assert result.code == code


def test_search_code_reports_unsupported_and_oversized_files(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_bytes(b"\xff")
    (tmp_path / "nul.py").write_bytes(b"a\x00b")
    write_text(tmp_path, "large.py", "a" * (256 * 1024 + 1))
    write_text(tmp_path, "good.py", "auth\n")

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (SearchMatch("good.py", 1, "auth"),)
    assert result.skipped == (
        SkippedFile("bad.py", "unsupported_content"),
        SkippedFile("large.py", "file_too_large"),
        SkippedFile("nul.py", "unsupported_content"),
    )
    assert not result.truncated


def test_search_code_file_size_limit_is_injectable(tmp_path: Path) -> None:
    write_text(tmp_path, "file.py", "auth!")

    result = SearchCodeTool(tmp_path, max_file_bytes=4).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == ()
    assert result.skipped == (SkippedFile("file.py", "file_too_large"),)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes unavailable")
def test_search_code_reports_special_objects_without_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.mkfifo(tmp_path / "pipe")

    def forbidden_read(tool: ReadFileTool, path: str) -> ReadFileSuccess | ToolFailure:
        pytest.fail("A special object must not reach file reading")

    monkeypatch.setattr(ReadFileTool, "read_file", forbidden_read)

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.skipped == (SkippedFile("pipe", "not_a_file"),)


@pytest.mark.parametrize("line_count", [2, 3])
def test_search_code_exact_match_cap_is_complete_and_extra_match_truncates(
    tmp_path: Path, line_count: int
) -> None:
    write_text(tmp_path, "file.py", "auth\n" * line_count)

    result = SearchCodeTool(tmp_path, max_matches=2).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (
        SearchMatch("file.py", 1, "auth"),
        SearchMatch("file.py", 2, "auth"),
    )
    assert result.truncated == (line_count > 2)


def test_search_code_default_match_cap_returns_100_lines(tmp_path: Path) -> None:
    write_text(tmp_path, "file.py", "auth\n" * 101)

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert len(result.matches) == 100
    assert result.truncated


def test_search_code_truncation_is_deterministic_and_stops_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("z.py", "a/inside.py", "a.py"):
        write_text(tmp_path, name, "auth\n")
    calls: list[str] = []
    original_read = ReadFileTool.read_file

    def tracked_read(tool: ReadFileTool, path: str) -> ReadFileSuccess | ToolFailure:
        calls.append(path)
        return original_read(tool, path)

    monkeypatch.setattr(ReadFileTool, "read_file", tracked_read)

    result = SearchCodeTool(tmp_path, max_matches=1).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (SearchMatch("a.py", 1, "auth"),)
    assert result.truncated
    assert calls == ["a.py", "a/inside.py"]


def test_search_code_skipped_records_cover_processed_portion_when_truncated(
    tmp_path: Path,
) -> None:
    (tmp_path / "a_bad.py").write_bytes(b"\xff")
    write_text(tmp_path, "b.py", "auth\nauth\n")
    (tmp_path / "z_bad.py").write_bytes(b"\xff")

    result = SearchCodeTool(tmp_path, max_matches=1).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.skipped == (SkippedFile("a_bad.py", "unsupported_content"),)
    assert result.truncated


@pytest.mark.parametrize("entry_count", [3, 4])
def test_search_code_exact_entry_budget_and_overflow(
    tmp_path: Path, entry_count: int
) -> None:
    for index in range(entry_count):
        write_text(tmp_path, f"file_{index}.py", "auth\n")

    result = SearchCodeTool(tmp_path, max_entries=3).search_code(".", "auth")

    if entry_count == 3:
        assert isinstance(result, SearchCodeSuccess)
        assert len(result.matches) == 3
        assert not result.truncated
    else:
        assert isinstance(result, ToolFailure)
        assert result.code == "search_too_large"


def test_search_code_default_entry_budget_rejects_large_directory(
    tmp_path: Path,
) -> None:
    for index in range(1_001):
        (tmp_path / f"file_{index}").touch()

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert isinstance(result, ToolFailure)
    assert result.code == "search_too_large"


def test_search_code_entry_budget_is_global_across_directories(tmp_path: Path) -> None:
    write_text(tmp_path, "a.py", "auth\n")
    write_text(tmp_path, "nested/b.py", "auth\n")
    write_text(tmp_path, "nested/c.py", "auth\n")

    result = SearchCodeTool(tmp_path, max_entries=3).search_code(".", "auth")

    assert isinstance(result, ToolFailure)
    assert result.code == "search_too_large"


def test_search_code_child_listing_receives_remaining_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_text(tmp_path, "a.py", "auth\n")
    write_text(tmp_path, "nested/b.py", "auth\n")
    budgets: list[tuple[str, int, bool]] = []
    original_list = ListFilesTool.list_files

    def tracked_list(
        tool: ListFilesTool, path: str, include_hidden: bool = False
    ) -> ListFilesSuccess | ToolFailure:
        budgets.append((path, tool.max_entries, include_hidden))
        return original_list(tool, path, include_hidden=include_hidden)

    monkeypatch.setattr(ListFilesTool, "list_files", tracked_list)

    result = SearchCodeTool(tmp_path, max_entries=3).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert budgets == [(".", 3, True), ("nested", 1, True)]


def test_search_code_hidden_entries_count_but_hidden_descendants_are_not_scanned(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, ".hidden/inside.py", "auth\n")
    write_text(tmp_path, ".hidden.py", "auth\n")

    result = SearchCodeTool(tmp_path, max_entries=2).search_code(".", "auth")

    assert result == SearchCodeSuccess(".", "auth", (), (), False)
    overflow = SearchCodeTool(tmp_path, max_entries=1).search_code(".", "auth")
    assert isinstance(overflow, ToolFailure)
    assert overflow.code == "search_too_large"


def test_search_code_ignored_symlinks_still_count_toward_entry_budget(
    tmp_path: Path,
) -> None:
    (tmp_path / "alias").symlink_to(tmp_path, target_is_directory=True)

    result = SearchCodeTool(tmp_path, max_entries=0).search_code(".", "auth")

    assert isinstance(result, ToolFailure)
    assert result.code == "search_too_large"


@pytest.mark.parametrize("code", ["permission_denied", "directory_not_found"])
def test_search_code_directory_failure_discards_earlier_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
) -> None:
    write_text(tmp_path, "a.py", "auth\n")
    (tmp_path / "z").mkdir()
    original_list = ListFilesTool.list_files
    failure = ToolFailure(code, "Directory access failed.")

    def failed_list(
        tool: ListFilesTool, path: str, include_hidden: bool = False
    ) -> ListFilesSuccess | ToolFailure:
        if path == "z":
            return failure
        return original_list(tool, path, include_hidden=include_hidden)

    monkeypatch.setattr(ListFilesTool, "list_files", failed_list)

    assert SearchCodeTool(tmp_path).search_code(".", "auth") == failure


@pytest.mark.parametrize(
    "code", ["permission_denied", "file_not_found", "outside_repository", "not_a_file"]
)
def test_search_code_file_failure_discards_earlier_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
) -> None:
    write_text(tmp_path, "a.py", "auth\n")
    write_text(tmp_path, "z.py", "auth\n")
    original_read = ReadFileTool.read_file
    failure = ToolFailure(code, "File access failed.")

    def failed_read(tool: ReadFileTool, path: str) -> ReadFileSuccess | ToolFailure:
        return failure if path == "z.py" else original_read(tool, path)

    monkeypatch.setattr(ReadFileTool, "read_file", failed_read)

    assert SearchCodeTool(tmp_path).search_code(".", "auth") == failure


def test_search_code_file_disappears_after_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_text(tmp_path, "file.py", "auth\n")
    original_read = ReadFileTool.read_file

    def disappearing_read(
        tool: ReadFileTool, path: str
    ) -> ReadFileSuccess | ToolFailure:
        (tmp_path / path).unlink()
        return original_read(tool, path)

    monkeypatch.setattr(ReadFileTool, "read_file", disappearing_read)

    result = SearchCodeTool(tmp_path).search_code(".", "auth")

    assert isinstance(result, ToolFailure)
    assert result.code == "file_not_found"


def test_search_code_unexpected_exception_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_text(tmp_path, "file.py", "auth\n")

    def broken_read(tool: ReadFileTool, path: str) -> ReadFileSuccess | ToolFailure:
        raise RuntimeError("Unexpected defect")

    monkeypatch.setattr(ReadFileTool, "read_file", broken_read)

    with pytest.raises(RuntimeError, match="Unexpected defect"):
        SearchCodeTool(tmp_path).search_code(".", "auth")


def test_search_code_records_and_configuration_are_immutable(tmp_path: Path) -> None:
    match = SearchMatch("file.py", 1, "auth")
    skipped = SkippedFile("image.png", "unsupported_content")
    result = SearchCodeSuccess(".", "auth", (match,), (skipped,), False)
    tool = SearchCodeTool(tmp_path)

    with pytest.raises(FrozenInstanceError):
        match.text = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        skipped.code = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.truncated = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        tool.repository_root = tmp_path / "other"  # type: ignore[misc]


@pytest.mark.parametrize("limits", [(-1, 1, 1), (1, -1, 1), (1, 1, -1)])
def test_search_code_rejects_negative_limits(
    tmp_path: Path, limits: tuple[int, int, int]
) -> None:
    with pytest.raises(ValueError, match="Search limits must be non-negative"):
        SearchCodeTool(
            tmp_path,
            max_matches=limits[0],
            max_entries=limits[1],
            max_file_bytes=limits[2],
        )


def test_search_code_zero_match_limit_reports_truncation_for_a_match(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, "file.py", "auth\n")

    result = SearchCodeTool(tmp_path, max_matches=0).search_code(".", "auth")

    assert result == SearchCodeSuccess(".", "auth", (), (), True)


def test_search_code_zero_entry_budget_accepts_empty_scope(tmp_path: Path) -> None:
    assert SearchCodeTool(tmp_path, max_entries=0).search_code(
        ".", "auth"
    ) == SearchCodeSuccess(
        ".",
        "auth",
        (),
        (),
        False,
    )


def test_search_code_zero_file_byte_limit_accepts_empty_and_skips_nonempty(
    tmp_path: Path,
) -> None:
    write_text(tmp_path, "empty.py", "")
    write_text(tmp_path, "file.py", "auth\n")

    result = SearchCodeTool(tmp_path, max_file_bytes=0).search_code(".", "auth")

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == ()
    assert result.skipped == (SkippedFile("file.py", "file_too_large"),)


def test_search_code_deep_traversal_uses_stack_without_recursive_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    depth_limit = 1_100

    def deep_listing(
        tool: ListFilesTool,
        path: str,
        include_hidden: bool = False,
    ) -> ListFilesSuccess:
        depth = 0 if path == "." else len(Path(path).parts)
        child = "file.py" if depth == depth_limit else "d"
        kind = EntryKind.FILE if depth == depth_limit else EntryKind.DIRECTORY
        assert tool.max_entries >= 1
        return ListFilesSuccess(
            directory=path,
            entries=(ListEntry((Path(path) / child).as_posix(), kind),),
        )

    def synthetic_read(tool: ReadFileTool, path: str) -> ReadFileSuccess:
        return ReadFileSuccess(path=path, content="auth\n")

    monkeypatch.setattr(ListFilesTool, "list_files", deep_listing)
    monkeypatch.setattr(ReadFileTool, "read_file", synthetic_read)

    result = SearchCodeTool(tmp_path, max_entries=depth_limit + 1).search_code(
        ".", "auth"
    )

    assert isinstance(result, SearchCodeSuccess)
    assert result.matches == (SearchMatch("d/" * depth_limit + "file.py", 1, "auth"),)
