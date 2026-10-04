from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from .tools.registry import ToolMetadata, ToolResult


@dataclass(frozen=True)
class ToolRequest:
    id: str
    tool_name: str
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Tool request id must be nonempty")
        if not self.tool_name:
            raise ValueError("Tool name must be nonempty")
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True)
class ToolResultMessage:
    request_id: str
    tool_name: str
    result: ToolResult

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("Tool result request id must be nonempty")
        if not self.tool_name:
            raise ValueError("Tool result tool name must be nonempty")


@dataclass(frozen=True)
class ToolInteraction:
    request: ToolRequest
    result: ToolResultMessage

    def __post_init__(self) -> None:
        if self.request.id != self.result.request_id:
            raise ValueError("Tool request and result ids must match")
        if self.request.tool_name != self.result.tool_name:
            raise ValueError("Tool request and result names must match")


@dataclass(frozen=True)
class ModelRequest:
    instructions: str
    question: str
    context: tuple[ToolInteraction, ...] = ()
    tools: tuple[ToolMetadata, ...] = ()

    def __post_init__(self) -> None:
        if not self.instructions:
            raise ValueError("Model instructions must be nonempty")
        if not self.question:
            raise ValueError("Model question must be nonempty")


@dataclass(frozen=True)
class TextResponse:
    text: str


@dataclass(frozen=True)
class ModelFailure:
    code: str
    message: str
    retryable: bool


ModelResponse = TextResponse | ToolRequest
ModelResult = ModelResponse | ModelFailure


class Model(Protocol):
    def generate(self, request: ModelRequest) -> ModelResult: ...
