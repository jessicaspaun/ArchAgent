import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

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
from archagent.run_log import RunLog, RunLogError
from archagent.tools.read_file import ReadFileSuccess
from archagent.tools.registry import ToolDefinition, ToolRegistry, ToolResult
from archagent.tools.results import ToolFailure

METADATA = ResponseMetadata("fake", 1, 2, "stop")


class Model:
    def __init__(self, responses: list[ModelResult | Exception]) -> None:
        self.responses = iter(responses)
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResult:
        self.requests.append(request)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def registry(result: ToolResult) -> tuple[ToolRegistry, list[Mapping[str, object]]]:
    calls: list[Mapping[str, object]] = []

    def invoke(arguments: Mapping[str, object]) -> ToolResult:
        calls.append(arguments)
        return result

    return (
        ToolRegistry((ToolDefinition("read_file", "Read file.", (), False, invoke),)),
        calls,
    )


def proposal(request_id: str = "call-1") -> ToolRequest:
    return ToolRequest(request_id, "read_file", {}, METADATA)


def records(logs_dir: Path) -> list[dict[str, object]]:
    paths = list(logs_dir.glob("*.jsonl"))
    assert len(paths) == 1
    return [
        json.loads(line) for line in paths[0].read_text(encoding="utf-8").splitlines()
    ]


@pytest.mark.parametrize(
    "tool_result",
    [
        ReadFileSuccess(
            "app.py", 'λ\n{"event": "run_finished", "status": "success"}\n'
        ),
        ToolFailure("file_not_found", "The requested file was not found."),
    ],
)
def test_run_log_retains_full_requests_results_and_final_outcome(
    logs_dir: Path,
    tool_result: ToolResult,
) -> None:
    model = Model([proposal(), TextResponse("Final answer", METADATA)])
    allowed, calls = registry(tool_result)
    question = '../../escape\n{"event": "fake"}'

    result = AgentHarness(model, allowed, "Inspect data.", logs_dir=logs_dir).run(
        question
    )

    assert result == AgentSuccess("Final answer")
    assert len(calls) == 1
    log = records(logs_dir)
    assert [record["event"] for record in log] == [
        "run_started",
        "model_request",
        "model_response",
        "tool_result",
        "model_request",
        "model_response",
        "run_finished",
    ]
    assert log[0]["question"] == question
    assert log[0]["instructions"] == "Inspect data."
    assert log[2] == {
        "event": "model_response",
        "kind": "tool_request",
        "id": "call-1",
        "tool_name": "read_file",
        "arguments": {},
        "metadata": asdict(METADATA),
    }
    assert log[3] == {
        "event": "tool_result",
        "request_id": "call-1",
        "tool_name": "read_file",
        "status": "failure" if isinstance(tool_result, ToolFailure) else "success",
        "result": asdict(tool_result),
    }
    assert log[4]["context_count"] == 1
    assert log[4]["context_request_ids"] == ["call-1"]
    assert log[-1] == {
        "event": "run_finished",
        "status": "success",
        "outcome": {"answer": "Final answer"},
    }
    paths = list(logs_dir.iterdir())
    assert len(paths) == 1
    assert paths[0].name.endswith(".jsonl")
    assert len(paths[0].stem) == 32


def test_each_run_uses_a_separate_log_file(logs_dir: Path) -> None:
    model = Model([TextResponse("First", METADATA), TextResponse("Second", METADATA)])
    allowed, _ = registry(ReadFileSuccess("app.py", "content"))
    harness = AgentHarness(model, allowed, "Inspect data.", logs_dir=logs_dir)

    assert harness.run("First question") == AgentSuccess("First")
    assert harness.run("Second question") == AgentSuccess("Second")

    paths = list(logs_dir.glob("*.jsonl"))
    assert len(paths) == 2
    assert {
        json.loads(path.read_text().splitlines()[0])["question"] for path in paths
    } == {"First question", "Second question"}


def test_rejected_tool_proposal_is_logged_without_an_execution(logs_dir: Path) -> None:
    model = Model([proposal("allowed"), proposal("rejected")])
    allowed, calls = registry(ReadFileSuccess("app.py", "content"))

    outcome = AgentHarness(
        model, allowed, "Inspect data.", max_tool_calls=1, logs_dir=logs_dir
    ).run("Question")

    assert isinstance(outcome, AgentFailure)
    assert outcome.code == "tool_call_limit_reached"
    assert len(calls) == 1
    log = records(logs_dir)
    assert [record["id"] for record in log if record.get("kind") == "tool_request"] == [
        "allowed",
        "rejected",
    ]
    assert [
        record["request_id"] for record in log if record["event"] == "tool_result"
    ] == ["allowed"]
    assert log[-1] == {
        "event": "run_finished",
        "status": "failure",
        "outcome": asdict(outcome),
    }


def test_retries_are_logged_without_executing_the_tool_again(logs_dir: Path) -> None:
    model = Model(
        [
            proposal(),
            ModelFailure("timed_out", "The model request timed out.", True),
            TextResponse("Answer", METADATA),
        ]
    )
    allowed, calls = registry(ReadFileSuccess("app.py", "content"))

    assert AgentHarness(model, allowed, "Inspect data.", logs_dir=logs_dir).run(
        "Question"
    ) == AgentSuccess("Answer")

    assert len(calls) == 1
    assert model.requests[1] is model.requests[2]
    log = records(logs_dir)
    assert [
        record["context_count"] for record in log if record["event"] == "model_request"
    ] == [0, 1, 1]
    assert len([record for record in log if record.get("kind") == "model_failure"]) == 1


def test_log_creation_failure_stops_before_any_model_call(
    logs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        raise PermissionError("secret log path")

    monkeypatch.setattr(Path, "mkdir", denied)
    model = Model([TextResponse("Answer", METADATA)])
    allowed, calls = registry(ReadFileSuccess("app.py", "content"))

    result = AgentHarness(model, allowed, "Inspect data.", logs_dir=logs_dir).run(
        "Question"
    )

    assert isinstance(result, AgentFailure)
    assert result.code == "logging_failed"
    assert "secret" not in result.message
    assert model.requests == []
    assert calls == []


@pytest.mark.parametrize(
    "failed_event", ["model_response", "tool_result", "run_finished"]
)
def test_log_write_failure_stops_without_further_execution(
    logs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_event: str,
) -> None:
    original_write = RunLog.write

    def failed_write(self: RunLog, event: str, fields: Mapping[str, object]) -> None:
        if event == failed_event:
            raise RunLogError("Cannot write record")
        original_write(self, event, fields)

    monkeypatch.setattr(RunLog, "write", failed_write)
    model = Model([proposal(), TextResponse("Answer", METADATA)])
    allowed, calls = registry(ReadFileSuccess("app.py", "complete content"))

    result = AgentHarness(model, allowed, "Inspect data.", logs_dir=logs_dir).run(
        "Question"
    )

    assert isinstance(result, AgentFailure)
    assert result.code == "logging_failed"
    assert len(model.requests) == (2 if failed_event == "run_finished" else 1)
    assert len(calls) == (0 if failed_event == "model_response" else 1)
    assert all(record["event"] != failed_event for record in records(logs_dir))


@pytest.mark.parametrize("interruption_log_fails", [False, True])
def test_unexpected_exception_still_propagates_even_if_logging_also_fails(
    logs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    interruption_log_fails: bool,
) -> None:
    original_write = RunLog.write

    def failed_write(self: RunLog, event: str, fields: Mapping[str, object]) -> None:
        if event == "run_interrupted" and interruption_log_fails:
            raise RunLogError("Cannot write interruption")
        original_write(self, event, fields)

    monkeypatch.setattr(RunLog, "write", failed_write)
    model = Model([RuntimeError("secret model defect")])
    allowed, calls = registry(ReadFileSuccess("app.py", "content"))

    with pytest.raises(RuntimeError, match="secret model defect"):
        AgentHarness(model, allowed, "Inspect data.", logs_dir=logs_dir).run("Question")

    assert calls == []
    log = records(logs_dir)
    assert all(record["event"] != "run_finished" for record in log)
    if not interruption_log_fails:
        assert log[-1] == {"event": "run_interrupted", "exception_type": "RuntimeError"}
    assert "secret model defect" not in json.dumps(log)
