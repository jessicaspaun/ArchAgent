from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from archagent.model import (
    Model,
    ModelFailure,
    ModelRequest,
    ModelResult,
    ResponseMetadata,
    TextResponse,
    ToolInteraction,
    ToolRequest,
    ToolResultMessage,
)
from archagent.tools.list_files import ListFilesSuccess
from archagent.tools.registry import (
    ToolAdapter,
    ToolDefinition,
    ToolRegistry,
    create_repository_registry,
)
from archagent.tools.results import ToolFailure


def make_tool_request() -> ToolRequest:
    return ToolRequest(
        id="call-1",
        tool_name="list_files",
        arguments={"path": "."},
        metadata=ResponseMetadata("fake", 1, 2, "stop"),
    )


def make_tool_result(
    result: ListFilesSuccess | ToolFailure | None = None,
) -> ToolResultMessage:
    return ToolResultMessage(
        request_id="call-1",
        tool_name="list_files",
        result=result or ListFilesSuccess(directory=".", entries=()),
    )


def test_model_request_contains_separate_immutable_fields() -> None:
    interaction = ToolInteraction(make_tool_request(), make_tool_result())
    request = ModelRequest(
        instructions="Investigate before answering.",
        question="Where is state stored?",
        context=(interaction,),
    )

    assert request.instructions == "Investigate before answering."
    assert request.question == "Where is state stored?"
    assert request.context == (interaction,)
    assert request.tools == ()
    with pytest.raises(FrozenInstanceError):
        request.question = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("instructions", "question", "message"),
    [
        ("", "Question", "Model instructions must be nonempty"),
        ("Instructions", "", "Model question must be nonempty"),
    ],
)
def test_model_request_rejects_empty_required_text(
    instructions: str,
    question: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ModelRequest(instructions=instructions, question=question)


def test_tool_request_copies_arguments_into_read_only_mapping() -> None:
    arguments: dict[str, object] = {"path": "."}
    request = ToolRequest(
        "call-1",
        "list_files",
        arguments,
        ResponseMetadata("fake", 1, 2, "stop"),
    )

    arguments["path"] = "changed"

    assert dict(request.arguments) == {"path": "."}
    with pytest.raises(TypeError):
        request.arguments["path"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    ("request_id", "tool_name", "message"),
    [
        ("", "list_files", "Tool request id must be nonempty"),
        ("call-1", "", "Tool name must be nonempty"),
    ],
)
def test_tool_request_rejects_empty_identity_fields(
    request_id: str,
    tool_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ToolRequest(
            request_id,
            tool_name,
            {},
            ResponseMetadata("fake", 1, 2, "stop"),
        )


@pytest.mark.parametrize(
    ("request_id", "tool_name", "message"),
    [
        ("", "list_files", "Tool result request id must be nonempty"),
        ("call-1", "", "Tool result tool name must be nonempty"),
    ],
)
def test_tool_result_rejects_empty_identity_fields(
    request_id: str,
    tool_name: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ToolResultMessage(
            request_id,
            tool_name,
            ListFilesSuccess(directory=".", entries=()),
        )


@pytest.mark.parametrize("mismatch", ["id", "name"])
def test_tool_interaction_requires_matching_request_and_result(
    mismatch: str,
) -> None:
    request = make_tool_request()
    result = ToolResultMessage(
        request_id="other" if mismatch == "id" else request.id,
        tool_name="read_file" if mismatch == "name" else request.tool_name,
        result=ListFilesSuccess(directory=".", entries=()),
    )

    with pytest.raises(
        ValueError, match=f"Tool request and result {mismatch}s must match"
    ):
        ToolInteraction(request, result)


@pytest.mark.parametrize(
    "result",
    [
        ListFilesSuccess(directory=".", entries=()),
        ToolFailure(code="permission_denied", message="Access denied."),
    ],
)
def test_context_accepts_successful_and_failed_tool_results(
    result: ListFilesSuccess | ToolFailure,
) -> None:
    interaction = ToolInteraction(make_tool_request(), make_tool_result(result))

    request = ModelRequest("Instructions", "Question", context=(interaction,))

    assert request.context[0].result.result == result


class TextModel:
    def generate(self, request: ModelRequest) -> ModelResult:
        return TextResponse(
            f"Answer to: {request.question}",
            ResponseMetadata("fake", 1, 2, "stop"),
        )


class RequestingModel:
    def generate(self, request: ModelRequest) -> ModelResult:
        return make_tool_request()


def generate(model: Model, request: ModelRequest) -> ModelResult:
    return model.generate(request)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (
            TextModel(),
            TextResponse(
                "Answer to: Question",
                ResponseMetadata("fake", 1, 2, "stop"),
            ),
        ),
        (RequestingModel(), make_tool_request()),
    ],
)
def test_structural_model_protocol_accepts_both_response_actions(
    model: Model,
    expected: ModelResult,
) -> None:
    assert generate(model, ModelRequest("Instructions", "Question")) == expected


def test_model_failure_is_an_immutable_controlled_result() -> None:
    failure = ModelFailure(
        code="rate_limited",
        message="The model provider rate limit was reached.",
        retryable=True,
    )

    assert failure.code == "rate_limited"
    assert failure.retryable is True
    with pytest.raises(FrozenInstanceError):
        failure.retryable = False  # type: ignore[misc]


@pytest.mark.parametrize(
    ("model", "input_tokens", "output_tokens", "stop_reason", "message"),
    [
        ("", 1, 2, "stop", "Response model must be nonempty"),
        ("model", -1, 2, "stop", "Response token counts must be non-negative"),
        ("model", 1, -2, "stop", "Response token counts must be non-negative"),
        ("model", 1, 2, "", "Response stop reason must be nonempty"),
    ],
)
def test_response_metadata_rejects_invalid_values(
    model: str,
    input_tokens: int,
    output_tokens: int,
    stop_reason: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ResponseMetadata(model, input_tokens, output_tokens, stop_reason)


def test_unexpected_model_exception_propagates() -> None:
    class BrokenModel:
        def generate(self, request: ModelRequest) -> ModelResult:
            raise RuntimeError("Unexpected defect")

    with pytest.raises(RuntimeError, match="Unexpected defect"):
        generate(BrokenModel(), ModelRequest("Instructions", "Question"))


def test_model_receives_tool_metadata_without_execution_capability(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    protected = tmp_path / "protected"
    target.mkdir()
    protected.mkdir()
    registry = create_repository_registry(target, protected)
    request = ModelRequest(
        instructions="Investigate before answering.",
        question="What files exist?",
        tools=registry.discover(),
    )

    assert tuple(tool.name for tool in request.tools) == (
        "list_files",
        "read_file",
        "search_code",
    )
    assert {field.name for field in fields(ModelRequest)} == {
        "instructions",
        "question",
        "context",
        "tools",
    }
    assert not any(
        isinstance(value, (ToolRegistry, ToolDefinition)) or callable(value)
        for tool in request.tools
        for value in vars(tool).values()
    )


def test_returning_tool_request_does_not_invoke_registry_adapter() -> None:
    called = False

    def adapter(arguments: Mapping[str, object]) -> ToolFailure:
        nonlocal called
        called = True
        return ToolFailure("called", "called")

    typed_adapter: ToolAdapter = adapter
    registry = ToolRegistry(
        (
            ToolDefinition(
                name="sample",
                description="Sample tool.",
                arguments=(),
                allow_extra_arguments=False,
                adapter=typed_adapter,
            ),
        )
    )
    request = ModelRequest("Instructions", "Question", tools=registry.discover())

    result = generate(RequestingModel(), request)

    assert isinstance(result, ToolRequest)
    assert called is False
