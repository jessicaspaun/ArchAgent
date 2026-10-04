import json
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from types import TracebackType
from urllib.request import Request

import pytest

import archagent.ollama as ollama_module
from archagent.model import (
    ModelFailure,
    ModelRequest,
    ResponseMetadata,
    TextResponse,
    ToolInteraction,
    ToolRequest,
    ToolResultMessage,
)
from archagent.ollama import OllamaConfig, OllamaModel
from archagent.tools.list_files import ListFilesSuccess
from archagent.tools.registry import create_repository_registry


class FakeHttpResponse:
    def __init__(self, data: Mapping[str, object]) -> None:
        self._stream = BytesIO(json.dumps(data).encode("utf-8"))

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stream.close()

    def read(self) -> bytes:
        return self._stream.read()


def test_ollama_sends_text_request_and_translates_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[Request, float]] = []

    def fake_urlopen(request: Request, timeout: float) -> FakeHttpResponse:
        captured.append((request, timeout))
        return FakeHttpResponse(
            {
                "model": "qwen2.5:7b",
                "message": {"role": "assistant", "content": "ready"},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 25,
                "eval_count": 2,
            }
        )

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)

    result = OllamaModel().generate(
        ModelRequest(
            instructions="Answer in one short sentence.",
            question="Reply with the word ready.",
        )
    )

    assert result == TextResponse(
        text="ready",
        metadata=ResponseMetadata(
            model="qwen2.5:7b",
            input_tokens=25,
            output_tokens=2,
            stop_reason="stop",
        ),
    )
    assert len(captured) == 1
    request, timeout = captured[0]
    assert request.full_url == "http://127.0.0.1:11434/api/chat"
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert timeout == 60.0
    assert isinstance(request.data, bytes)
    assert json.loads(request.data) == {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "Answer in one short sentence."},
            {"role": "user", "content": "Reply with the word ready."},
        ],
        "stream": False,
    }


def test_ollama_uses_configured_model_base_url_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[Request, float]] = []

    def fake_urlopen(request: Request, timeout: float) -> FakeHttpResponse:
        captured.append((request, timeout))
        return FakeHttpResponse(
            {
                "model": "custom-model",
                "message": {"role": "assistant", "content": "answer"},
                "done_reason": "length",
                "prompt_eval_count": 3,
                "eval_count": 4,
            }
        )

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)
    model = OllamaModel(
        OllamaConfig(
            model="custom-model",
            base_url="http://localhost:9999/",
            timeout_seconds=12.5,
        )
    )

    result = model.generate(ModelRequest("Instructions", "Question"))

    assert isinstance(result, TextResponse)
    request, timeout = captured[0]
    assert request.full_url == "http://localhost:9999/api/chat"
    assert timeout == 12.5
    assert isinstance(request.data, bytes)
    assert json.loads(request.data)["model"] == "custom-model"


def test_ollama_rejects_unsupported_request_before_network_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_urlopen(request: Request, timeout: float) -> FakeHttpResponse:
        pytest.fail("Unsupported requests must not contact Ollama")

    monkeypatch.setattr(ollama_module, "urlopen", forbidden_urlopen)
    tool_request = ToolRequest(
        "call-1",
        "list_files",
        {"path": "."},
        ResponseMetadata("fake", 1, 2, "stop"),
    )
    tool_result = ToolResultMessage(
        "call-1",
        "list_files",
        ListFilesSuccess(directory=".", entries=()),
    )
    request = ModelRequest(
        "Instructions",
        "Question",
        context=(ToolInteraction(tool_request, tool_result),),
    )

    result = OllamaModel().generate(request)

    assert result == ModelFailure(
        code="unsupported_request",
        message="The Ollama adapter does not yet support prior tool context.",
        retryable=False,
    )


def test_ollama_sends_tool_schemas_and_translates_one_tool_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Request] = []

    def fake_urlopen(request: Request, timeout: float) -> FakeHttpResponse:
        captured.append(request)
        return FakeHttpResponse(
            {
                "model": "qwen2.5:7b",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-provider",
                            "function": {
                                "index": 0,
                                "name": "list_files",
                                "arguments": {"path": ""},
                            },
                        }
                    ],
                },
                "done_reason": "stop",
                "prompt_eval_count": 195,
                "eval_count": 19,
            }
        )

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)
    target = tmp_path / "target"
    protected = tmp_path / "protected"
    target.mkdir()
    protected.mkdir()
    tools = create_repository_registry(target, protected).discover()

    result = OllamaModel().generate(
        ModelRequest("Use repository tools.", "List root files.", tools=tools)
    )

    assert result == ToolRequest(
        id="call-provider",
        tool_name="list_files",
        arguments={"path": ""},
        metadata=ResponseMetadata("qwen2.5:7b", 195, 19, "stop"),
    )
    assert isinstance(captured[0].data, bytes)
    payload = json.loads(captured[0].data)
    assert [tool["function"]["name"] for tool in payload["tools"]] == [
        "list_files",
        "read_file",
        "search_code",
    ]
    list_schema = payload["tools"][0]["function"]["parameters"]
    assert list_schema == {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "A repository-relative directory path.",
                "minLength": 1,
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Include entries whose names begin with a dot.",
                "default": False,
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }


def test_ollama_generates_id_when_tool_call_omits_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: float) -> FakeHttpResponse:
        return FakeHttpResponse(
            {
                "model": "qwen2.5:7b",
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "list_files", "arguments": {}}}
                    ],
                },
                "done_reason": "stop",
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    class FixedUuid:
        hex = "fixed"

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(ollama_module, "uuid4", lambda: FixedUuid())
    target = tmp_path / "target"
    protected = tmp_path / "protected"
    target.mkdir()
    protected.mkdir()
    tools = create_repository_registry(target, protected).discover()

    result = OllamaModel().generate(
        ModelRequest("Instructions", "Question", tools=tools)
    )

    assert isinstance(result, ToolRequest)
    assert result.id == "call_fixed"


@pytest.mark.parametrize(
    "message",
    [
        {
            "content": "text",
            "tool_calls": [{"function": {"name": "list_files", "arguments": {}}}],
        },
        {
            "content": "",
            "tool_calls": [
                {"function": {"name": "list_files", "arguments": {}}},
                {"function": {"name": "read_file", "arguments": {}}},
            ],
        },
        {
            "content": "",
            "tool_calls": [{"function": {"name": "unknown", "arguments": {}}}],
        },
        {
            "content": "",
            "tool_calls": [{"function": {"name": "list_files", "arguments": []}}],
        },
        {"content": "", "tool_calls": "invalid"},
    ],
)
def test_ollama_returns_controlled_failure_for_invalid_action_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: dict[str, object],
) -> None:
    def fake_urlopen(request: Request, timeout: float) -> FakeHttpResponse:
        return FakeHttpResponse(
            {
                "model": "qwen2.5:7b",
                "message": message,
                "done_reason": "stop",
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    monkeypatch.setattr(ollama_module, "urlopen", fake_urlopen)
    target = tmp_path / "target"
    protected = tmp_path / "protected"
    target.mkdir()
    protected.mkdir()
    tools = create_repository_registry(target, protected).discover()

    result = OllamaModel().generate(
        ModelRequest("Instructions", "Question", tools=tools)
    )

    assert result == ModelFailure(
        code="invalid_response",
        message="Ollama returned a response that ArchAgent could not validate.",
        retryable=True,
    )


@pytest.mark.parametrize(
    ("model", "base_url", "timeout", "message"),
    [
        ("", "http://localhost:11434", 60.0, "Ollama model must be nonempty"),
        ("model", "", 60.0, "Ollama base URL must be nonempty"),
        ("model", "http://localhost:11434", 0, "Ollama timeout must be positive"),
        ("model", "http://localhost:11434", -1, "Ollama timeout must be positive"),
    ],
)
def test_ollama_config_rejects_invalid_values(
    model: str,
    base_url: str,
    timeout: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        OllamaConfig(model=model, base_url=base_url, timeout_seconds=timeout)
