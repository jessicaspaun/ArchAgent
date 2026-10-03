from pathlib import Path

import pytest

from archagent.tools._paths import (
    OutsideRepositoryError,
    resolve_repository_path,
    resolve_within_repository,
)


def test_resolve_repository_path_returns_resolved_root_and_contained_target(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    directory = repository / "directory"
    directory.mkdir(parents=True)

    assert resolve_repository_path(repository, "directory") == (
        repository.resolve(),
        directory.resolve(),
    )


def test_resolve_repository_path_uses_filesystem_parent_and_symlink_semantics(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    target = repository / "package" / "nested"
    target.mkdir(parents=True)
    alias = repository / "alias"
    alias.symlink_to(target, target_is_directory=True)

    assert resolve_repository_path(repository, "alias/../file.py") == (
        repository.resolve(),
        repository / "package" / "file.py",
    )


@pytest.mark.parametrize("kind", ["absolute", "parent", "symlink"])
def test_resolve_repository_path_rejects_outside_targets(
    tmp_path: Path,
    kind: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    if kind == "absolute":
        requested: str | Path = outside
    elif kind == "parent":
        requested = "../outside"
    else:
        alias = repository / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        requested = "alias"

    with pytest.raises(OutsideRepositoryError):
        resolve_repository_path(repository, requested)


def test_resolve_repository_path_leaves_contained_existence_to_caller(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    assert resolve_repository_path(repository, "missing/file.py") == (
        repository.resolve(),
        repository / "missing" / "file.py",
    )


def test_resolve_within_repository_retains_established_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    resolved_root = repository.resolve()
    original_resolve = Path.resolve

    def tracked_resolve(path: Path, strict: bool = False) -> Path:
        if path == resolved_root:
            pytest.fail("The established repository root must not be re-resolved")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", tracked_resolve)

    assert resolve_within_repository(resolved_root, "file.py") == (
        resolved_root / "file.py"
    )


def test_resolve_repository_path_propagates_resolution_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    original_resolve = Path.resolve

    def denied_resolve(path: Path, strict: bool = False) -> Path:
        if path == repository:
            raise PermissionError("denied")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", denied_resolve)

    with pytest.raises(PermissionError, match="denied"):
        resolve_repository_path(repository, ".")
