import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.request import Request, urlopen

from .model import (
    ModelFailure,
    ModelRequest,
    ModelResult,
    ResponseMetadata,
    TextResponse,
)


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
        if request.context or request.tools:
            return ModelFailure(
                code="unsupported_request",
                message=(
                    "The text-only Ollama adapter does not yet support context "
                    "or tool definitions."
                ),
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
        http_request = Request(
            f"{self.config.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(http_request, timeout=self.config.timeout_seconds) as response:
            response_data: object = json.loads(response.read())

        root = _object_mapping(response_data, "response")
        message = _object_mapping(root.get("message"), "message")
        return TextResponse(
            text=_string_field(message, "content"),
            metadata=ResponseMetadata(
                model=_string_field(root, "model"),
                input_tokens=_integer_field(root, "prompt_eval_count"),
                output_tokens=_integer_field(root, "eval_count"),
                stop_reason=_string_field(root, "done_reason"),
            ),
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
