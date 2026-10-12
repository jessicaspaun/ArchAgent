from dataclasses import asdict, dataclass, field
from pathlib import Path

from .model import (
    Model,
    ModelFailure,
    ModelRequest,
    ModelResult,
    TextResponse,
    ToolInteraction,
    ToolResultMessage,
)
from .run_log import RunLog, RunLogError, model_result_record
from .tools.registry import ToolMetadata, ToolRegistry
from .tools.results import ToolFailure


@dataclass(frozen=True)
class AgentSuccess:
    answer: str

    def __post_init__(self) -> None:
        if not self.answer:
            raise ValueError("Agent answer must be nonempty")


@dataclass(frozen=True)
class AgentFailure:
    code: str
    message: str

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Agent failure code must be nonempty")
        if not self.message:
            raise ValueError("Agent failure message must be nonempty")


AgentResult = AgentSuccess | AgentFailure


@dataclass(frozen=True)
class AgentHarness:
    model: Model
    registry: ToolRegistry
    instructions: str
    max_model_retries: int = 2
    max_tool_calls: int = 4
    logs_dir: Path = field(kw_only=True)

    def __post_init__(self) -> None:
        if not self.instructions:
            raise ValueError("Agent instructions must be nonempty")
        if type(self.max_model_retries) is not int or self.max_model_retries < 0:
            raise ValueError("Maximum model retries must be a non-negative integer")
        if type(self.max_tool_calls) is not int or self.max_tool_calls < 0:
            raise ValueError("Maximum tool calls must be a non-negative integer")

    def run(self, question: str) -> AgentResult:
        tools = self.registry.discover()
        # Validate the caller's question before creating any run artifact.
        ModelRequest(self.instructions, question, tools=tools)
        try:
            with RunLog(self.logs_dir, self.registry.repository_root) as log:
                log.write(
                    "run_started",
                    {
                        "instructions": self.instructions,
                        "question": question,
                        "tools": [asdict(tool) for tool in tools],
                        "max_tool_calls": self.max_tool_calls,
                        "max_model_retries": self.max_model_retries,
                    },
                )
                try:
                    outcome = self._run(question, tools, log)
                    log.write(
                        "run_finished",
                        {
                            "status": (
                                "success"
                                if isinstance(outcome, AgentSuccess)
                                else "failure"
                            ),
                            "outcome": asdict(outcome),
                        },
                    )
                except RunLogError:
                    raise
                except Exception as error:
                    try:
                        log.write(
                            "run_interrupted", {"exception_type": type(error).__name__}
                        )
                    except RunLogError:
                        pass
                    raise
            return outcome
        except RunLogError:
            return AgentFailure(
                "logging_failed",
                "The investigation stopped because its run log could not be written.",
            )

    def _run(
        self, question: str, tools: tuple[ToolMetadata, ...], log: RunLog
    ) -> AgentResult:
        retries_remaining = self.max_model_retries
        context: tuple[ToolInteraction, ...] = ()
        while True:
            request = ModelRequest(
                instructions=self.instructions,
                question=question,
                context=context,
                tools=tools,
            )
            result, retries_remaining = self._generate(request, retries_remaining, log)

            if isinstance(result, ModelFailure):
                return _to_agent_failure(result)
            if isinstance(result, TextResponse):
                return AgentSuccess(result.text)
            if len(context) >= self.max_tool_calls:
                return AgentFailure(
                    code="tool_call_limit_reached",
                    message="The agent reached the tool-call limit for this run.",
                )

            tool_result = self.registry.invoke(result.tool_name, result.arguments)
            interaction = ToolInteraction(
                request=result,
                result=ToolResultMessage(
                    request_id=result.id,
                    tool_name=result.tool_name,
                    result=tool_result,
                ),
            )
            log.write(
                "tool_result",
                {
                    "request_id": result.id,
                    "tool_name": result.tool_name,
                    "status": (
                        "failure" if isinstance(tool_result, ToolFailure) else "success"
                    ),
                    "result": asdict(tool_result),
                },
            )
            context += (interaction,)

    def _generate(
        self, request: ModelRequest, retries_remaining: int, log: RunLog
    ) -> tuple[ModelResult, int]:
        while True:
            log.write(
                "model_request",
                {
                    "context_count": len(request.context),
                    "context_request_ids": [
                        interaction.request.id for interaction in request.context
                    ],
                },
            )
            result = self.model.generate(request)
            log.write("model_response", model_result_record(result))
            if not isinstance(result, ModelFailure) or not result.retryable:
                return result, retries_remaining
            if retries_remaining == 0:
                return (
                    ModelFailure(
                        code="model_retry_exhausted",
                        message=(
                            "The model could not complete the request within the "
                            "retry limit."
                        ),
                        retryable=False,
                    ),
                    retries_remaining,
                )
            retries_remaining -= 1


def _to_agent_failure(failure: ModelFailure) -> AgentFailure:
    return AgentFailure(code=failure.code, message=failure.message)
