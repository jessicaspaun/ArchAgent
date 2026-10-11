import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from types import TracebackType
from typing import TextIO
from uuid import uuid4

from .model import ModelFailure, ModelResult, TextResponse, ToolRequest


class RunLogError(Exception):
    """A known filesystem failure prevents reliable run logging."""


class RunLog:
    def __init__(self, directory: Path, repository_root: Path | None) -> None:
        try:
            directory = directory.resolve()
            if repository_root is not None and directory.is_relative_to(
                repository_root
            ):
                raise RunLogError("Run logs must remain outside the target repository.")
            directory.mkdir(parents=True, exist_ok=True)
            self._stream: TextIO = (directory / f"{uuid4().hex}.jsonl").open(
                "x", encoding="utf-8"
            )
        except OSError as error:
            raise RunLogError("The run log could not be created.") from error

    def __enter__(self) -> "RunLog":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self._stream.close()
        except OSError as error:
            if exception is None:
                raise RunLogError("The run log could not be closed.") from error

    def write(self, event: str, fields: Mapping[str, object]) -> None:
        # Encode before the I/O boundary so serialization defects still propagate.
        record = json.dumps({"event": event, **fields}) + "\n"
        try:
            self._stream.write(record)
            self._stream.flush()
        except OSError as error:
            raise RunLogError("The run log could not be written.") from error


def model_result_record(result: ModelResult) -> dict[str, object]:
    if isinstance(result, ToolRequest):
        return {
            "kind": "tool_request",
            "id": result.id,
            "tool_name": result.tool_name,
            "arguments": dict(result.arguments),
            "metadata": asdict(result.metadata),
        }
    if isinstance(result, TextResponse):
        return {"kind": "text_response", **asdict(result)}
    if isinstance(result, ModelFailure):
        return {"kind": "model_failure", **asdict(result)}
