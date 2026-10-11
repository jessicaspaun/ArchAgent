from pathlib import Path


class OutsideRepositoryError(Exception):
    """The resolved target lies outside its repository boundary."""


def resolve_repository_path(
    repository_root: Path,
    requested_path: str | Path,
) -> tuple[Path, Path]:
    """Resolve a path and enforce containment within its repository root."""
    root = repository_root.resolve()
    return root, resolve_within_repository(root, requested_path)


def resolve_within_repository(
    resolved_root: Path,
    requested_path: str | Path,
) -> Path:
    """Resolve a path against an already established repository boundary."""
    target = (resolved_root / requested_path).resolve()
    if not target.is_relative_to(resolved_root):
        raise OutsideRepositoryError
    return target
