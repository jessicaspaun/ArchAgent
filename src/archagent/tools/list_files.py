from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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

    def list_files(
        self,
        path: str,
        include_hidden: bool = False,
    ) -> ListFilesSuccess:
        root = self.repository_root.resolve()
        directory = (root / path).resolve()

        entries: list[ListEntry] = []

        for child in directory.iterdir():
            if child.is_dir():
                kind = EntryKind.DIRECTORY
            elif child.is_file():
                kind = EntryKind.FILE
            else:
                kind = EntryKind.OTHER

            entries.append(
                ListEntry(
                    path=child.relative_to(root).as_posix(),
                    kind=kind,
                )
            )

        entries.sort(key=lambda entry: entry.path)

        return ListFilesSuccess(
            directory=directory.relative_to(root).as_posix(),
            entries=tuple(entries),
        )