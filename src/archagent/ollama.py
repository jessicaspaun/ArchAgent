import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.request import Request, urlopen
from uuid import uuid4

from .model import (
    ModelFailure,
    ModelRequest,
    ModelResult,
    ResponseMetadata,
    TextResponse,
    ToolRequest,
)
from .tools.registry import ArgumentMetadata, OptionalArgumentMetadata, ToolMetadata


@dataclass(frozen=True)
class OllamaConfig:
    model: str = "qwen2.5:7b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("Ollama model must be nonempty")
        if not self.base_url:
            raise ValueError("Ollama base URL must be nonempty")
        if self.timeout_seconds <= 0:
            raise ValueError("Ollama timeout must be positive")
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))


@dataclass(frozen=True)
class OllamaModel:
    config: OllamaConfig = field(default_factory=OllamaConfig)

    def generate(self, request: ModelRequest) -> ModelResult:
        if request.context:
            return ModelFailure(
                code="unsupported_request",
                message=("The Ollama adapter does not yet support prior tool context."),
                retryable=False,
            )

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.question},
            ],
            "stream": False,
        }
        if request.tools:
            payload["tools"] = [_tool_schema(tool) for tool in request.tools]
        http_request = Request(
            f"{self.config.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                response_data: object = json.loads(response.read())

            root = _object_mapping(response_data, "response")
            message = _object_mapping(root.get("message"), "message")
            metadata = ResponseMetadata(
                model=_string_field(root, "model"),
                input_tokens=_integer_field(root, "prompt_eval_count"),
                output_tokens=_integer_field(root, "eval_count"),
                stop_reason=_string_field(root, "done_reason"),
            )
            return _model_response(message, metadata, request.tools)
        except ValueError:
            return ModelFailure(
                code="invalid_response",
                message="Ollama returned a response that ArchAgent could not validate.",
                retryable=True,
            )


def _tool_schema(tool: ToolMetadata) -> dict[str, object]:
    properties = {
        argument.name: _argument_schema(argument) for argument in tool.arguments
    }
    required = [argument.name for argument in tool.arguments if argument.required]
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": tool.allow_extra_arguments,
            },
        },
    }


def _argument_schema(argument: ArgumentMetadata) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": argument.type,
        "description": argument.description,
    }
    if "nonempty" in argument.constraints:
        schema["minLength"] = 1
    if isinstance(argument, OptionalArgumentMetadata):
        schema["default"] = argument.default
    return schema


def _model_response(
    message: Mapping[str, object],
    metadata: ResponseMetadata,
    tools: tuple[ToolMetadata, ...],
) -> ModelResult:
    content = _string_field(message, "content")
    raw_calls = message.get("tool_calls")
    if raw_calls is None or raw_calls == []:
        return TextResponse(text=content, metadata=metadata)
    if not isinstance(raw_calls, list):
        raise ValueError("Ollama tool_calls must be a list")
    if content or len(raw_calls) != 1:
        raise ValueError("Ollama response must contain exactly one action")

    call = _object_mapping(raw_calls[0], "tool call")
    function = _object_mapping(call.get("function"), "tool function")
    tool_name = _string_field(function, "name")
    if tool_name not in {tool.name for tool in tools}:
        raise ValueError("Ollama requested a tool that was not offered")
    arguments = _object_mapping(function.get("arguments"), "tool arguments")

    raw_id = call.get("id")
    if raw_id is None:
        request_id = f"call_{uuid4().hex}"
    elif isinstance(raw_id, str) and raw_id:
        request_id = raw_id
    else:
        raise ValueError("Ollama tool call id must be a nonempty string")

    return ToolRequest(
        id=request_id,
        tool_name=tool_name,
        arguments=arguments,
        metadata=metadata,
    )


def _object_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Ollama {name} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"Ollama {name} keys must be strings")
    return value


def _string_field(data: Mapping[str, object], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise ValueError(f"Ollama field '{name}' must be a string")
    return value


def _integer_field(data: Mapping[str, object], name: str) -> int:
    value = data.get(name)
    if type(value) is not int:
        raise ValueError(f"Ollama field '{name}' must be an integer")
    return value
