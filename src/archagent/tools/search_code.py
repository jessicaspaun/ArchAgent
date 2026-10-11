from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from .list_files import EntryKind, ListEntry, ListFilesTool
from .read_file import ReadFileTool
from .results import ToolFailure


@dataclass(frozen=True)
class SearchMatch:
    path: str
    line_number: int
    text: str


@dataclass(frozen=True)
class SkippedFile:
    path: str
    code: str


@dataclass(frozen=True)
class SearchCodeSuccess:
    directory: str
    query: str
    matches: tuple[SearchMatch, ...]
    skipped: tuple[SkippedFile, ...]
    truncated: bool


@dataclass(frozen=True)
class SearchCodeTool:
    repository_root: Path
    max_matches: int = 100
    max_entries: int = 1_000
    max_file_bytes: int = 256 * 1024

    def __post_init__(self) -> None:
        if self.max_matches < 0 or self.max_entries < 0 or self.max_file_bytes < 0:
            raise ValueError("Search limits must be non-negative")

    def search_code(
        self, path: str, query: str, include_hidden: bool = False
    ) -> SearchCodeSuccess | ToolFailure:
        directory = Path(path).as_posix()
        pending = [ListEntry(path=directory, kind=EntryKind.DIRECTORY)]
        reader = ReadFileTool(self.repository_root, max_bytes=self.max_file_bytes)
        matches: list[SearchMatch] = []
        skipped: list[SkippedFile] = []
        examined = 0
        truncated = False

        # An explicit stack avoids Python recursion-depth limits. Directory
        # listings consume the remaining global budget, including hidden entries.
        while pending and not truncated:
            entry = pending.pop()
            if entry.kind == EntryKind.DIRECTORY:
                listing = ListFilesTool(
                    self.repository_root, max_entries=self.max_entries - examined
                ).list_files(entry.path, include_hidden=True)
                if isinstance(listing, ToolFailure):
                    if listing.code == "directory_too_large":
                        return ToolFailure(
                            code="search_too_large",
                            message="The search exceeds the directory-entry budget.",
                        )
                    return listing

                examined += len(listing.entries)
                # The trailing slash positions a directory's descendants in
                # file-path order (e.g. a.py precedes a/file.py). Reverse the
                # order for the last-in-first-out stack.
                children = sorted(
                    listing.entries,
                    key=lambda child: child.path
                    + ("/" if child.kind == EntryKind.DIRECTORY else ""),
                    reverse=True,
                )
                for child in children:
                    if child.kind == EntryKind.SYMLINK:
                        continue
                    if not include_hidden and Path(child.path).name.startswith("."):
                        continue
                    pending.append(child)
                continue

            if entry.kind == EntryKind.OTHER:
                skipped.append(SkippedFile(path=entry.path, code="not_a_file"))
                continue

            result = reader.read_file(entry.path)
            if isinstance(result, ToolFailure):
                if result.code in {"unsupported_content", "file_too_large"}:
                    skipped.append(SkippedFile(path=entry.path, code=result.code))
                    continue
                return result

            # Universal line endings cover LF, CRLF, and CR, while preserving
            # other Unicode characters that str.splitlines() would split.
            with StringIO(result.content, newline=None) as lines:
                for line_number, line in enumerate(lines, start=1):
                    text = line.removesuffix("\n")
                    if query not in text:
                        continue
                    if len(matches) == self.max_matches:
                        truncated = True
                        break
                    matches.append(
                        SearchMatch(
                            path=result.path, line_number=line_number, text=text
                        )
                    )

        return SearchCodeSuccess(
            directory=directory,
            query=query,
            matches=tuple(
                sorted(matches, key=lambda match: (match.path, match.line_number))
            ),
            skipped=tuple(sorted(skipped, key=lambda item: item.path)),
            truncated=truncated,
        )
