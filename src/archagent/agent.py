from dataclasses import dataclass

from .model import (
    Model,
    ModelFailure,
    ModelRequest,
    ModelResult,
    TextResponse,
    ToolInteraction,
    ToolRequest,
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

    def __post_init__(self) -> None:
        if not self.instructions:
            raise ValueError("Agent instructions must be nonempty")
        if self.max_model_retries < 0:
            raise ValueError("Maximum model retries must be non-negative")

    def run(self, question: str) -> AgentResult:
        tools = self.registry.discover()
        retries_remaining = self.max_model_retries
        initial_request = ModelRequest(
            instructions=self.instructions,
            question=question,
            tools=tools,
        )
        initial_result, retries_remaining = self._generate(
            initial_request, retries_remaining
        )

        if isinstance(initial_result, ModelFailure):
            return _to_agent_failure(initial_result)
        if isinstance(initial_result, TextResponse):
            return AgentSuccess(initial_result.text)

        tool_result = self.registry.invoke(
            initial_result.tool_name, initial_result.arguments
        )
        interaction = ToolInteraction(
            request=initial_result,
            result=ToolResultMessage(
                request_id=initial_result.id,
                tool_name=initial_result.tool_name,
                result=tool_result,
            ),
        )
        follow_up_request = ModelRequest(
            instructions=self.instructions,
            question=question,
            context=(interaction,),
            tools=tools,
        )
        follow_up_result, _ = self._generate(follow_up_request, retries_remaining)

        if isinstance(follow_up_result, ModelFailure):
            return _to_agent_failure(follow_up_result)
        if isinstance(follow_up_result, ToolRequest):
            return AgentFailure(
                code="tool_call_limit_reached",
                message="The agent reached the one-tool-call limit for this run.",
            )
        return AgentSuccess(follow_up_result.text)

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
