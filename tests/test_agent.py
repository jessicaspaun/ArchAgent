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
    def __init__(self, results: list[ModelResult | Exception]) -> None:
        self._results = iter(results)
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResult:
        self.requests.append(request)
        result = next(self._results)
        if isinstance(result, Exception):
            raise result
        return result


class BrokenModel:
    def generate(self, request: ModelRequest) -> ModelResult:
        raise RuntimeError("Unexpected model defect")


class RecordingTool:
    def __init__(
        self,
        result: ListFilesSuccess | ToolFailure | None = None,
        error: Exception | None = None,
        error_after: int = 0,
    ) -> None:
        self.result = result or ListFilesSuccess(
            directory=".", entries=(ListEntry("a.py", EntryKind.FILE),)
        )
        self.error = error
        self.error_after = error_after
        self.arguments: list[Mapping[str, object]] = []

    def __call__(self, arguments: ValidatedArguments) -> ListFilesSuccess | ToolFailure:
        self.arguments.append(arguments)
        if self.error is not None and len(self.arguments) > self.error_after:
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

    result = AgentHarness(
        model, make_registry(tool), "Investigate.", max_tool_calls=1
    ).run("Question?")

    assert result == AgentFailure(
        code="tool_call_limit_reached",
        message="The agent reached the tool-call limit for this run.",
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


@pytest.mark.parametrize(("attempts", "limit"), [(2, 4), (4, 4), (6, 6)])
def test_harness_preserves_ordered_history_and_accepts_answers_within_the_limit(
    attempts: int,
    limit: int,
) -> None:
    calls = [tool_request(f"call-{index}") for index in range(attempts)]
    model = ScriptedModel([*calls, TextResponse("Final answer", METADATA)])
    tool = RecordingTool()
    registry = make_registry(tool)

    result = AgentHarness(model, registry, "Investigate.", max_tool_calls=limit).run(
        "Question?"
    )

    assert result == AgentSuccess("Final answer")
    assert len(tool.arguments) == attempts
    assert len(model.requests) == attempts + 1
    for index, request in enumerate(model.requests):
        assert request.instructions == "Investigate."
        assert request.question == "Question?"
        assert request.tools == registry.discover()
        assert len(request.context) == index
        assert [interaction.request for interaction in request.context] == calls[:index]
        for interaction in request.context:
            assert interaction.result.request_id == interaction.request.id
            assert interaction.result.tool_name == interaction.request.tool_name
            assert interaction.result.result == tool.result


def test_repeated_tool_calls_stop_at_four_attempts_without_executing_a_fifth() -> None:
    model = ScriptedModel([tool_request(f"call-{index}") for index in range(5)])
    tool = RecordingTool()

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert result == AgentFailure(
        "tool_call_limit_reached", "The agent reached the tool-call limit for this run."
    )
    assert len(tool.arguments) == 4
    assert all(dict(arguments) == {"path": "."} for arguments in tool.arguments)
    assert len(model.requests) == 5
    assert len(model.requests[-1].context) == 4


@pytest.mark.parametrize("failure_kind", ["tool", "invalid_arguments", "unknown_tool"])
def test_failed_tool_attempts_also_exhaust_the_limit(failure_kind: str) -> None:
    failure = ToolFailure("permission_denied", "The directory cannot be accessed.")
    tool = RecordingTool(result=failure)
    name = "unknown" if failure_kind == "unknown_tool" else "list_files"
    path = "" if failure_kind == "invalid_arguments" else "."
    model = ScriptedModel(
        [
            ToolRequest(f"call-{index}", name, {"path": path}, METADATA)
            for index in range(5)
        ]
    )

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert isinstance(result, AgentFailure)
    assert result.code == "tool_call_limit_reached"
    assert len(model.requests) == 5
    assert len(model.requests[-1].context) == 4
    assert len(tool.arguments) == (4 if failure_kind == "tool" else 0)
    expected_code = failure.code if failure_kind == "tool" else failure_kind
    for interaction in model.requests[-1].context:
        observed = interaction.result.result
        assert isinstance(observed, ToolFailure)
        assert observed.code == expected_code


def test_harness_can_recover_from_invalid_arguments_with_a_new_tool_request() -> None:
    invalid = ToolRequest("invalid", "list_files", {"path": ""}, METADATA)
    valid = tool_request("valid")
    tool = RecordingTool()
    model = ScriptedModel([invalid, valid, TextResponse("Recovered answer", METADATA)])

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert result == AgentSuccess("Recovered answer")
    assert len(tool.arguments) == 1
    history = model.requests[-1].context
    assert [interaction.request.id for interaction in history] == ["invalid", "valid"]
    assert isinstance(history[0].result.result, ToolFailure)
    assert history[0].result.result.code == "invalid_arguments"
    assert history[1].result.result == tool.result


@pytest.mark.parametrize("answer", [True, False])
def test_zero_tool_budget_allows_only_an_immediate_answer(answer: bool) -> None:
    response: ModelResult = (
        TextResponse("Immediate answer", METADATA) if answer else tool_request()
    )
    model = ScriptedModel([response])
    tool = RecordingTool()

    result = AgentHarness(
        model, make_registry(tool), "Investigate.", max_tool_calls=0
    ).run("Question?")

    if answer:
        assert result == AgentSuccess("Immediate answer")
    else:
        assert isinstance(result, AgentFailure)
        assert result.code == "tool_call_limit_reached"
    assert len(model.requests) == 1
    assert tool.arguments == []


@pytest.mark.parametrize("limit", [-1, 1.5, True, "4"])
def test_harness_rejects_invalid_tool_limits(limit: object) -> None:
    with pytest.raises(
        ValueError, match="Maximum tool calls must be a non-negative integer"
    ):
        AgentHarness(
            ScriptedModel([]),
            make_registry(),
            "Investigate.",
            max_tool_calls=limit,  # type: ignore[arg-type]
        )


def test_model_retry_budget_is_not_replenished_by_later_tool_success() -> None:
    tool = RecordingTool()
    model = ScriptedModel(
        [
            retryable_failure(),
            tool_request("first"),
            retryable_failure(),
            tool_request("second"),
            retryable_failure(),
        ]
    )

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert isinstance(result, AgentFailure)
    assert result.code == "model_retry_exhausted"
    assert len(tool.arguments) == 2
    assert [len(request.context) for request in model.requests] == [0, 0, 1, 1, 2]
    assert model.requests[0] is model.requests[1]
    assert model.requests[2] is model.requests[3]


def test_final_answer_opportunity_can_use_remaining_model_retries() -> None:
    model = ScriptedModel(
        [
            *(tool_request(f"call-{index}") for index in range(4)),
            retryable_failure(),
            TextResponse("Final answer", METADATA),
        ]
    )
    tool = RecordingTool()

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert result == AgentSuccess("Final answer")
    assert len(tool.arguments) == 4
    assert len(model.requests) == 6
    assert model.requests[-2] is model.requests[-1]
    assert len(model.requests[-1].context) == 4


def test_non_retryable_model_failure_after_multiple_tools_stops_the_run() -> None:
    failure = ModelFailure(
        "provider_rejected_request", "The request was rejected.", False
    )
    model = ScriptedModel([tool_request("first"), tool_request("second"), failure])
    tool = RecordingTool()

    result = AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert result == AgentFailure(failure.code, failure.message)
    assert len(tool.arguments) == 2
    assert len(model.requests) == 3


def test_unexpected_model_exception_after_multiple_tools_propagates() -> None:
    model = ScriptedModel(
        [
            tool_request("first"),
            tool_request("second"),
            RuntimeError("Later model defect"),
        ]
    )
    tool = RecordingTool()

    with pytest.raises(RuntimeError, match="Later model defect"):
        AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert len(tool.arguments) == 2
    assert len(model.requests) == 3


def test_unexpected_tool_exception_after_an_observation_propagates() -> None:
    model = ScriptedModel([tool_request("first"), tool_request("second")])
    tool = RecordingTool(error=RuntimeError("Later tool defect"), error_after=1)

    with pytest.raises(RuntimeError, match="Later tool defect"):
        AgentHarness(model, make_registry(tool), "Investigate.").run("Question?")

    assert len(tool.arguments) == 2
    assert len(model.requests) == 2
    assert len(model.requests[-1].context) == 1


def test_each_run_gets_a_fresh_tool_budget_and_no_prior_observations() -> None:
    calls = [tool_request(f"call-{index}") for index in range(5)]
    model = ScriptedModel([*calls, *calls[:4], TextResponse("Second answer", METADATA)])
    tool = RecordingTool()
    harness = AgentHarness(model, make_registry(tool), "Investigate.")

    first = harness.run("First question?")
    second = harness.run("Second question?")

    assert isinstance(first, AgentFailure)
    assert first.code == "tool_call_limit_reached"
    assert second == AgentSuccess("Second answer")
    assert len(tool.arguments) == 8
    assert [len(request.context) for request in model.requests] == [0, 1, 2, 3, 4] * 2
    assert all(request.question == "First question?" for request in model.requests[:5])
    assert all(request.question == "Second question?" for request in model.requests[5:])
