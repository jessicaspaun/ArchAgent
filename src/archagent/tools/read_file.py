from dataclasses import dataclass
from os import fstat
from pathlib import Path
from stat import S_ISREG

from .results import ToolFailure


@dataclass(frozen=True)
class ReadFileSuccess:
    path: str
    content: str


@dataclass(frozen=True)
class ReadFileTool:
    repository_root: Path
    max_bytes: int = 256 * 1024

    def __post_init__(self) -> None:
        if self.max_bytes < 0:
            raise ValueError("max_bytes must be non-negative")

    def read_file(self, path: str) -> ReadFileSuccess | ToolFailure:
        try:
            root = self.repository_root.resolve()
            target = (root / path).resolve()

            if not target.is_relative_to(root):
                return ToolFailure(
                    code="outside_repository",
                    message="The requested file is outside the repository.",
                )

            # Reject directories and special objects before opening for a read.
            if not S_ISREG(target.stat().st_mode):
                return ToolFailure(
                    code="not_a_file",
                    message="The requested path is not a regular file.",
                )

            # A binary read preserves line endings and bounds work even if the
            # file grows after the metadata check.
            with target.open("rb") as stream:
                current_target = target.resolve()
                if not current_target.is_relative_to(root):
                    return ToolFailure(
                        code="outside_repository",
                        message="The requested file is outside the repository.",
                    )

                try:
                    opened = fstat(stream.fileno())
                except OSError:
                    # In-memory test streams have no operating-system file
                    # descriptor. Real files always take the identity check.
                    opened = None
                if opened is not None:
                    current = current_target.stat()
                    if (opened.st_dev, opened.st_ino) != (
                        current.st_dev,
                        current.st_ino,
                    ):
                        return ToolFailure(
                            code="file_not_found",
                            message=(
                                "The requested file changed before it could be read."
                            ),
                        )

                data = stream.read(self.max_bytes + 1)

            if len(data) > self.max_bytes:
                return ToolFailure(
                    code="file_too_large",
                    message="The requested file exceeds the byte limit.",
                )

            if b"\x00" in data:
                return ToolFailure(
                    code="unsupported_content",
                    message="The requested file contains NUL bytes.",
                )

            content = data.decode("utf-8", errors="strict")
        except FileNotFoundError:
            return ToolFailure(
                code="file_not_found",
                message="The requested file does not exist.",
            )
        except (IsADirectoryError, NotADirectoryError):
            return ToolFailure(
                code="not_a_file",
                message="The requested path is not a regular file.",
            )
        except PermissionError:
            return ToolFailure(
                code="permission_denied",
                message="Permission to read the requested file was denied.",
            )
        except UnicodeDecodeError:
            return ToolFailure(
                code="unsupported_content",
                message="The requested file is not valid UTF-8.",
            )

        return ReadFileSuccess(path=Path(path).as_posix(), content=content)
