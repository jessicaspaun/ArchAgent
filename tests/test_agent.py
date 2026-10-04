from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import pytest

from archagent.agent import AgentFailure, AgentHarness, AgentSuccess
from archagent.model import (
    ModelFailure,
    ModelRequest,
    ModelResult,
    ResponseMetadata,
    TextResponse,
    ToolRequest,
)
from archagent.tools.list_files import EntryKind, ListEntry, ListFilesSuccess
from archagent.tools.registry import (
    ArgumentConstraint,
    ArgumentDefinition,
    ArgumentType,
    ToolDefinition,
    ToolRegistry,
    ValidatedArguments,
)
from archagent.tools.results import ToolFailure

METADATA = ResponseMetadata("fake", 1, 2, "stop")


class ScriptedModel:
    def __init__(self, results: list[ModelResult]) -> None:
        self._results = iter(results)
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResult:
        self.requests.append(request)
        return next(self._results)


class BrokenModel:
    def generate(self, request: ModelRequest) -> ModelResult:
        raise RuntimeError("Unexpected model defect")


class RecordingTool:
    def __init__(
        self,
        result: ListFilesSuccess | ToolFailure | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or ListFilesSuccess(
            directory=".", entries=(ListEntry("a.py", EntryKind.FILE),)
        )
        self.error = error
        self.arguments: list[Mapping[str, object]] = []

    def __call__(self, arguments: ValidatedArguments) -> ListFilesSuccess | ToolFailure:
        self.arguments.append(arguments)
        if self.error is not None:
            raise self.error
        return self.result


def make_registry(tool: RecordingTool | None = None) -> ToolRegistry:
    adapter = tool or RecordingTool()
    return ToolRegistry(
        (
            ToolDefinition(
                name="list_files",
                description="List files.",
                arguments=(
                    ArgumentDefinition(
                        name="path",
                        argument_type=ArgumentType.STRING,
                        required=True,
                        description="Repository-relative directory.",
                        constraints=(
                            ArgumentConstraint.NONEMPTY,
                            ArgumentConstraint.REPOSITORY_RELATIVE,
                        ),
                    ),
                ),
                allow_extra_arguments=False,
                adapter=adapter,
            ),
        )
    )


def tool_request(request_id: str = "call-1") -> ToolRequest:
    return ToolRequest(request_id, "list_files", {"path": "."}, METADATA)


def retryable_failure(code: str = "timed_out") -> ModelFailure:
    return ModelFailure(code, "The model request failed.", retryable=True)


def test_agent_results_are_validated_and_immutable() -> None:
    success = AgentSuccess("Final answer")
    failure = AgentFailure("model_failed", "The model failed.")

    assert success.answer == "Final answer"
    assert failure.code == "model_failed"
    with pytest.raises(FrozenInstanceError):
        success.answer = "Changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="Agent answer must be nonempty"):
        AgentSuccess("")
    with pytest.raises(ValueError, match="Agent failure code must be nonempty"):
        AgentFailure("", "Message")
    with pytest.raises(ValueError, match="Agent failure message must be nonempty"):
        AgentFailure("code", "")


@pytest.mark.parametrize(
    ("instructions", "max_model_retries", "message"),
    [
        ("", 2, "Agent instructions must be nonempty"),
        ("Investigate.", -1, "Maximum model retries must be non-negative"),
    ],
)
def test_harness_rejects_invalid_configuration(
    instructions: str, max_model_retries: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        AgentHarness(
            ScriptedModel([]),
            make_registry(),
            instructions,
            max_model_retries,
        )


def test_harness_returns_an_immediate_text_answer() -> None:
    model = ScriptedModel([TextResponse("Final answer", METADATA)])
    registry = make_registry()

    result = AgentHarness(model, registry, "Investigate.").run("Question?")

    assert result == AgentSuccess("Final answer")
    assert model.requests == [
        ModelRequest(
            instructions="Investigate.",
            question="Question?",
            tools=registry.discover(),
        )
    ]


def test_harness_executes_one_tool_and_returns_the_follow_up_answer() -> None:
    request = tool_request()
    model = ScriptedModel([request, TextResponse("Grounded answer", METADATA)])
    tool = RecordingTool()
    registry = make_registry(tool)

    result = AgentHarness(model, registry, "Investigate.").run("Question?")

    assert result == AgentSuccess("Grounded answer")
    assert len(tool.arguments) == 1
    assert dict(tool.arguments[0]) == {"path": "."}
    assert len(model.requests) == 2
    assert model.requests[1].question == "Question?"
    assert model.requests[1].tools == registry.discover()
    assert len(model.requests[1].context) == 1
    interaction = model.requests[1].context[0]
    assert interaction.request is request
    assert interaction.result.request_id == request.id
    assert interaction.result.tool_name == request.tool_name
    assert interaction.result.result == tool.result


@pytest.mark.parametrize(
    "tool_result",
    [
        ToolFailure("invalid_arguments", "The tool arguments are invalid."),
        ToolFailure("path_outside_repository", "The path is outside the repository."),
    ],
)
def test_harness_returns_controlled_tool_failures_to_the_model(
    tool_result: ToolFailure,
) -> None:
    model = ScriptedModel(
        [tool_request(), TextResponse("I could not inspect that path.", METADATA)]
    )
    registry = make_registry(RecordingTool(tool_result))

    result = AgentHarness(model, registry, "Investigate.").run("Question?")

    assert result == AgentSuccess("I could not inspect that path.")
    assert model.requests[1].context[0].result.result == tool_result


def test_harness_returns_unknown_tool_failure_to_the_model() -> None:
    unknown = ToolRequest("call-1", "delete_file", {"path": "a.py"}, METADATA)
    model = ScriptedModel(
        [unknown, TextResponse("That tool is unavailable.", METADATA)]
    )

    result = AgentHarness(model, make_registry(), "Investigate.").run("Question?")

    assert result == AgentSuccess("That tool is unavailable.")
    observed = model.requests[1].context[0].result.result
    assert observed == ToolFailure(
        code="unknown_tool",
        message="Unknown tool 'delete_file'. Available tools: list_files.",
    )


def test_harness_rejects_a_second_tool_request_without_executing_it() -> None:
    model = ScriptedModel([tool_request("call-1"), tool_request("call-2")])
    tool = RecordingTool()

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert result == AgentFailure(
        code="tool_call_limit_reached",
        message="The agent reached the one-tool-call limit for this run.",
    )
    assert len(tool.arguments) == 1


def test_harness_returns_non_retryable_model_failure_immediately() -> None:
    failure = ModelFailure(
        "authentication_failed",
        "Model authentication failed.",
        retryable=False,
    )
    model = ScriptedModel([failure])

    result = AgentHarness(model, make_registry(), "Investigate.").run("Question?")

    assert result == AgentFailure(failure.code, failure.message)
    assert len(model.requests) == 1


def test_harness_exhausts_two_retries_for_the_initial_model_request() -> None:
    model = ScriptedModel(
        [retryable_failure(), retryable_failure(), retryable_failure()]
    )

    result = AgentHarness(model, make_registry(), "Investigate.").run("Question?")

    assert result == AgentFailure(
        code="model_retry_exhausted",
        message="The model could not complete the request within the retry limit.",
    )
    assert len(model.requests) == 3
    assert model.requests[0] is model.requests[1]
    assert model.requests[1] is model.requests[2]


def test_model_retries_are_shared_across_the_entire_run() -> None:
    model = ScriptedModel(
        [
            retryable_failure(),
            tool_request(),
            retryable_failure(),
            retryable_failure(),
        ]
    )

    result = AgentHarness(model, make_registry(), "Investigate.").run("Question?")

    assert result == AgentFailure(
        code="model_retry_exhausted",
        message="The model could not complete the request within the retry limit.",
    )
    assert len(model.requests) == 4
    assert model.requests[0] is model.requests[1]
    assert model.requests[2] is model.requests[3]
    assert model.requests[1] is not model.requests[2]


def test_harness_can_recover_before_the_retry_budget_is_exhausted() -> None:
    model = ScriptedModel(
        [retryable_failure(), TextResponse("Recovered answer", METADATA)]
    )

    result = AgentHarness(model, make_registry(), "Investigate.").run("Question?")

    assert result == AgentSuccess("Recovered answer")
    assert len(model.requests) == 2


def test_unexpected_model_exception_propagates() -> None:
    with pytest.raises(RuntimeError, match="Unexpected model defect"):
        AgentHarness(BrokenModel(), make_registry(), "Investigate.").run("Question?")


def test_unexpected_tool_exception_propagates() -> None:
    tool = RecordingTool(error=RuntimeError("Unexpected tool defect"))
    model = ScriptedModel([tool_request()])

    with pytest.raises(RuntimeError, match="Unexpected tool defect"):
        AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")


def test_each_run_starts_with_fresh_context_and_retry_budget() -> None:
    model = ScriptedModel(
        [
            retryable_failure(),
            TextResponse("First answer", METADATA),
            retryable_failure(),
            retryable_failure(),
            TextResponse("Second answer", METADATA),
        ]
    )
    harness = AgentHarness(model, make_registry(), "Investigate.")

    first = harness.run("First question?")
    second = harness.run("Second question?")

    assert first == AgentSuccess("First answer")
    assert second == AgentSuccess("Second answer")
    assert all(request.context == () for request in model.requests)
    assert [request.question for request in model.requests] == [
        "First question?",
        "First question?",
        "Second question?",
        "Second question?",
        "Second question?",
    ]
