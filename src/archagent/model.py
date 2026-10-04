from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from .tools.registry import ToolMetadata, ToolResult


@dataclass(frozen=True)
class ResponseMetadata:
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("Response model must be nonempty")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("Response token counts must be non-negative")
        if not self.stop_reason:
            raise ValueError("Response stop reason must be nonempty")


@dataclass(frozen=True)
class ToolRequest:
    id: str
    tool_name: str
    arguments: Mapping[str, object]
    metadata: ResponseMetadata

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
    metadata: ResponseMetadata


@dataclass(frozen=True)
class ModelFailure:
    code: str
    message: str
    retryable: bool


ModelResponse = TextResponse | ToolRequest
ModelResult = ModelResponse | ModelFailure


class Model(Protocol):
    def generate(self, request: ModelRequest) -> ModelResult: ...
