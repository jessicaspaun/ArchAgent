from dataclasses import dataclass

from .model import (
    Model,
    ModelFailure,
    ModelRequest,
    ModelResult,
    TextResponse,
    ToolInteraction,
    ToolResultMessage,
)
from .tools.registry import ToolRegistry


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

    def __post_init__(self) -> None:
        if not self.instructions:
            raise ValueError("Agent instructions must be nonempty")
        if self.max_model_retries < 0:
            raise ValueError("Maximum model retries must be non-negative")
        if type(self.max_tool_calls) is not int or self.max_tool_calls < 0:
            raise ValueError("Maximum tool calls must be a non-negative integer")

    def run(self, question: str) -> AgentResult:
        tools = self.registry.discover()
        retries_remaining = self.max_model_retries
        context: tuple[ToolInteraction, ...] = ()
        while True:
            request = ModelRequest(
                instructions=self.instructions,
                question=question,
                context=context,
                tools=tools,
            )
            result, retries_remaining = self._generate(request, retries_remaining)

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
            context += (interaction,)

    def _generate(
        self, request: ModelRequest, retries_remaining: int
    ) -> tuple[ModelResult, int]:
        while True:
            result = self.model.generate(request)
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
