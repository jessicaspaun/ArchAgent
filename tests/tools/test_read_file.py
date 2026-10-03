import os
from dataclasses import FrozenInstanceError
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pytest

from archagent.tools.read_file import ReadFileSuccess, ReadFileTool
from archagent.tools.results import ToolFailure


@pytest.mark.parametrize(
    "content",
    ["print('hello')\n", "", "café 🐍\n", "one\r\ntwo\rthree\n", "\ufefftext\n"],
)
def test_read_file_returns_exact_text(tmp_path: Path, content: str) -> None:
    target = tmp_path / "file.py"
    data = content.encode("utf-8")
    target.write_bytes(data)

    result = ReadFileTool(repository_root=tmp_path).read_file("file.py")

    assert result == ReadFileSuccess(path="file.py", content=content)
    assert target.read_bytes() == data


def test_read_file_hidden_file_and_extension_do_not_filter_text(tmp_path: Path) -> None:
    directory = tmp_path / ".hidden"
    directory.mkdir()
    (directory / "text.png").write_bytes(b"ordinary text")

    result = ReadFileTool(repository_root=tmp_path).read_file("./.hidden//text.png")

    assert result == ReadFileSuccess(path=".hidden/text.png", content="ordinary text")


def test_read_file_internal_file_symlink_preserves_alias(tmp_path: Path) -> None:
    (tmp_path / "actual.py").write_bytes(b"content")
    (tmp_path / "alias.py").symlink_to(tmp_path / "actual.py")

    result = ReadFileTool(repository_root=tmp_path).read_file("alias.py")

    assert result == ReadFileSuccess(path="alias.py", content="content")


def test_read_file_internal_directory_symlink_preserves_alias(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "file.py").write_bytes(b"content")
    (tmp_path / "alias").symlink_to(actual, target_is_directory=True)

    result = ReadFileTool(repository_root=tmp_path).read_file("alias/file.py")

    assert result == ReadFileSuccess(path="alias/file.py", content="content")


def test_read_file_parent_traversal_preserves_caller_path(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    (tmp_path / "file.py").write_bytes(b"content")

    result = ReadFileTool(repository_root=tmp_path).read_file("folder/../file.py")

    assert result == ReadFileSuccess(path="folder/../file.py", content="content")


def test_read_file_symlink_parent_uses_target_parent(tmp_path: Path) -> None:
    package = tmp_path / "package"
    (package / "nested").mkdir(parents=True)
    (package / "file.py").write_bytes(b"package content")
    (tmp_path / "file.py").write_bytes(b"root content")
    (tmp_path / "alias").symlink_to(package / "nested", target_is_directory=True)

    result = ReadFileTool(repository_root=tmp_path).read_file("alias/../file.py")

    assert result == ReadFileSuccess(path="alias/../file.py", content="package content")


@pytest.mark.parametrize("kind", ["absolute", "parent", "symlink", "symlink_parent"])
def test_read_file_rejects_outside_paths_before_opening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"private content")
    if kind == "absolute":
        requested = str(outside)
    elif kind == "parent":
        requested = "../outside.py"
    elif kind == "symlink":
        (repository / "alias.py").symlink_to(outside)
        requested = "alias.py"
    else:
        (repository / "alias").symlink_to(repository, target_is_directory=True)
        requested = "alias/../outside.py"

    def forbidden_open(path: Path, mode: str) -> BinaryIO:
        pytest.fail("An outside path must not be opened")

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = ReadFileTool(repository_root=repository).read_file(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "outside_repository"
    assert str(tmp_path) not in result.message


@pytest.mark.parametrize("use_symlink", [False, True])
def test_read_file_missing_target_returns_file_not_found(
    tmp_path: Path,
    use_symlink: bool,
) -> None:
    requested = "missing.py"
    if use_symlink:
        (tmp_path / "alias.py").symlink_to(tmp_path / requested)
        requested = "alias.py"

    result = ReadFileTool(repository_root=tmp_path).read_file(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "file_not_found"


@pytest.mark.parametrize("use_symlink", [False, True])
def test_read_file_directory_is_rejected_before_opening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_symlink: bool,
) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    requested = "directory"
    if use_symlink:
        (tmp_path / "alias").symlink_to(directory, target_is_directory=True)
        requested = "alias"

    def forbidden_open(path: Path, mode: str) -> BinaryIO:
        pytest.fail("A directory must not be opened for reading")

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = ReadFileTool(repository_root=tmp_path).read_file(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "not_a_file"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes unavailable")
@pytest.mark.parametrize("use_symlink", [False, True])
def test_read_file_special_object_is_rejected_before_opening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_symlink: bool,
) -> None:
    pipe = tmp_path / "pipe"
    os.mkfifo(pipe)
    requested = "pipe"
    if use_symlink:
        (tmp_path / "alias").symlink_to(pipe)
        requested = "alias"

    def forbidden_open(path: Path, mode: str) -> BinaryIO:
        pytest.fail("A special object must not be opened for reading")

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = ReadFileTool(repository_root=tmp_path).read_file(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "not_a_file"


@pytest.mark.parametrize("data", [b"\xff", b"\xc3", b"\x89PNG\r\n\x1a\n"])
def test_read_file_invalid_utf8_is_unsupported(tmp_path: Path, data: bytes) -> None:
    (tmp_path / "file.py").write_bytes(data)

    result = ReadFileTool(repository_root=tmp_path).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "unsupported_content"


@pytest.mark.parametrize("data", [b"\x00", b"hello\x00world"])
def test_read_file_nul_is_unsupported(tmp_path: Path, data: bytes) -> None:
    (tmp_path / "file.py").write_bytes(data)

    result = ReadFileTool(repository_root=tmp_path).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "unsupported_content"


@pytest.mark.parametrize("max_bytes", [4, 256 * 1024])
def test_read_file_exact_byte_limit_succeeds(tmp_path: Path, max_bytes: int) -> None:
    data = b"a" * max_bytes
    (tmp_path / "file.py").write_bytes(data)

    result = ReadFileTool(repository_root=tmp_path, max_bytes=max_bytes).read_file(
        "file.py"
    )

    assert result == ReadFileSuccess(path="file.py", content=data.decode("utf-8"))


@pytest.mark.parametrize("max_bytes", [4, 256 * 1024])
def test_read_file_one_byte_over_limit_fails(tmp_path: Path, max_bytes: int) -> None:
    (tmp_path / "file.py").write_bytes(b"a" * (max_bytes + 1))

    result = ReadFileTool(repository_root=tmp_path, max_bytes=max_bytes).read_file(
        "file.py"
    )

    assert isinstance(result, ToolFailure)
    assert result.code == "file_too_large"


def test_read_file_limit_counts_utf8_bytes(tmp_path: Path) -> None:
    (tmp_path / "file.py").write_bytes("ééé".encode("utf-8"))

    result = ReadFileTool(repository_root=tmp_path, max_bytes=4).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "file_too_large"


def test_read_file_oversize_takes_precedence_over_decoding(tmp_path: Path) -> None:
    (tmp_path / "file.py").write_bytes(b"\xff" * 5)

    result = ReadFileTool(repository_root=tmp_path, max_bytes=4).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "file_too_large"


def test_read_file_bounds_read_and_closes_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "file.py").touch()
    requested_sizes: list[int | None] = []

    class TrackingReader(BytesIO):
        def read(self, size: int | None = -1, /) -> bytes:
            requested_sizes.append(size)
            return super().read(size)

    # Simulate contents growing after the empty file's metadata check.
    stream = TrackingReader(b"a" * 100)

    def tracked_open(path: Path, mode: str) -> BinaryIO:
        assert mode == "rb"
        return stream

    monkeypatch.setattr(Path, "open", tracked_open)

    result = ReadFileTool(repository_root=tmp_path, max_bytes=4).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "file_too_large"
    assert requested_sizes == [5]
    assert stream.closed


@pytest.mark.parametrize("stage", ["resolve", "stat", "open", "read"])
def test_read_file_permission_failure_returns_safe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    target = tmp_path / "file.py"
    target.write_bytes(b"content")
    original_resolve = Path.resolve
    original_stat = Path.stat

    def denied_resolve(path: Path, strict: bool = False) -> Path:
        if path.name == "file.py":
            raise PermissionError(f"Access denied: {path}")
        return original_resolve(path, strict=strict)

    def denied_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path.name == "file.py":
            raise PermissionError(f"Access denied: {path}")
        return original_stat(path, follow_symlinks=follow_symlinks)

    class DeniedReader(BytesIO):
        def read(self, size: int | None = -1, /) -> bytes:
            raise PermissionError(f"Access denied: {target}")

    stream = DeniedReader()

    def denied_open(path: Path, mode: str) -> BinaryIO:
        if stage == "open":
            raise PermissionError(f"Access denied: {path}")
        return stream

    if stage == "resolve":
        monkeypatch.setattr(Path, "resolve", denied_resolve)
    elif stage == "stat":
        monkeypatch.setattr(Path, "stat", denied_stat)
    else:
        monkeypatch.setattr(Path, "open", denied_open)

    result = ReadFileTool(repository_root=tmp_path).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "permission_denied"
    assert str(tmp_path) not in result.message
    if stage == "read":
        assert stream.closed
    else:
        stream.close()


@pytest.mark.parametrize("use_symlink", [False, True])
def test_read_file_disappearing_target_returns_file_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_symlink: bool,
) -> None:
    target = tmp_path / "file.py"
    target.write_bytes(b"content")
    requested = "file.py"
    if use_symlink:
        (tmp_path / "alias.py").symlink_to(target)
        requested = "alias.py"
    original_open = Path.open

    def disappearing_open(path: Path, mode: str) -> BinaryIO:
        target.unlink()
        assert mode == "rb"
        return original_open(path, "rb")

    monkeypatch.setattr(Path, "open", disappearing_open)

    result = ReadFileTool(repository_root=tmp_path).read_file(requested)

    assert isinstance(result, ToolFailure)
    assert result.code == "file_not_found"


def test_read_file_target_becomes_directory_before_opening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "file.py"
    target.touch()
    original_open = Path.open

    def replaced_open(path: Path, mode: str) -> BinaryIO:
        target.unlink()
        target.mkdir()
        assert mode == "rb"
        return original_open(path, "rb")

    monkeypatch.setattr(Path, "open", replaced_open)

    result = ReadFileTool(repository_root=tmp_path).read_file("file.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "not_a_file"


def test_read_file_file_component_used_as_directory_returns_not_a_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "file.py").write_bytes(b"content")

    result = ReadFileTool(repository_root=tmp_path).read_file("file.py/child.py")

    assert isinstance(result, ToolFailure)
    assert result.code == "not_a_file"


def test_read_file_unexpected_exception_propagates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "file.py").touch()

    def broken_open(path: Path, mode: str) -> BinaryIO:
        raise RuntimeError("Unexpected defect")

    monkeypatch.setattr(Path, "open", broken_open)

    with pytest.raises(RuntimeError, match="Unexpected defect"):
        ReadFileTool(repository_root=tmp_path).read_file("file.py")


def test_read_file_success_is_immutable() -> None:
    result = ReadFileSuccess(path="file.py", content="content")

    with pytest.raises(FrozenInstanceError):
        result.content = "changed"  # type: ignore[misc]


def test_read_file_rejects_negative_byte_limit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_bytes must be non-negative"):
        ReadFileTool(repository_root=tmp_path, max_bytes=-1)


@pytest.mark.parametrize("data", [b"", b"a"])
def test_read_file_zero_limit_only_accepts_empty_file(
    tmp_path: Path, data: bytes
) -> None:
    (tmp_path / "file.py").write_bytes(data)

    result = ReadFileTool(repository_root=tmp_path, max_bytes=0).read_file("file.py")

    if data:
        assert isinstance(result, ToolFailure)
        assert result.code == "file_too_large"
    else:
        assert result == ReadFileSuccess(path="file.py", content="")
