from dataclasses import dataclass
from enum import StrEnum
from os import scandir
from pathlib import Path

from .results import ToolFailure


class EntryKind(StrEnum):
    DIRECTORY = "directory"
    FILE = "file"
    OTHER = "other"
    SYMLINK = "symlink"


@dataclass(frozen=True)
class ListEntry:
    path: str
    kind: EntryKind


@dataclass(frozen=True)
class ListFilesSuccess:
    directory: str
    entries: tuple[ListEntry, ...]


@dataclass(frozen=True)
class ListFilesTool:
    repository_root: Path
    max_entries: int = 1_000

    def __post_init__(self) -> None:
        if self.max_entries < 0:
            raise ValueError("max_entries must be non-negative")

    def list_files(
        self,
        path: str,
        include_hidden: bool = False,
    ) -> ListFilesSuccess | ToolFailure:
        entries: list[ListEntry] = []

        try:
            root = self.repository_root.resolve()
            directory = (root / path).resolve()

            if not directory.is_relative_to(root):
                return ToolFailure(
                    code="outside_repository",
                    message="provided directory is outside root boundary",
                )

            with scandir(directory) as children:
                current_directory = directory.resolve()
                if not current_directory.is_relative_to(root):
                    return ToolFailure(
                        code="outside_repository",
                        message="provided directory is outside root boundary",
                    )

                for count, child in enumerate(children, start=1):
                    # Count hidden entries too: the limit bounds scanning work.
                    if count > self.max_entries:
                        return ToolFailure(
                            code="directory_too_large",
                            message="The requested directory exceeds the entry limit.",
                        )

                    if not include_hidden and child.name.startswith("."):
                        continue

                    if child.is_symlink():
                        kind = EntryKind.SYMLINK
                    elif child.is_dir(follow_symlinks=False):
                        kind = EntryKind.DIRECTORY
                    elif child.is_file(follow_symlinks=False):
                        kind = EntryKind.FILE
                    else:
                        kind = EntryKind.OTHER

                    entries.append(
                        ListEntry(
                            path=(Path(path) / child.name).as_posix(),
                            kind=kind,
                        )
                    )
        except FileNotFoundError:
            return ToolFailure(
                code="directory_not_found",
                message="The requested directory does not exist.",
            )
        except NotADirectoryError:
            return ToolFailure(
                code="not_a_directory",
                message="The requested path is not a directory.",
            )
        except PermissionError:
            return ToolFailure(
                code="permission_denied",
                message="Permission to list the requested directory was denied.",
            )

        entries.sort(key=lambda entry: entry.path)

        return ListFilesSuccess(
            directory=Path(path).as_posix(),
            entries=tuple(entries),
        )
