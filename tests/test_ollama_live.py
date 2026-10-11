import os

import pytest

from archagent.model import ModelRequest, TextResponse
from archagent.ollama import OllamaModel


@pytest.mark.live_model
@pytest.mark.skipif(
    os.environ.get("ARCHAGENT_RUN_LIVE_MODEL_TESTS") != "1",
    reason="Set ARCHAGENT_RUN_LIVE_MODEL_TESTS=1 to call local Ollama.",
)
def test_live_ollama_text_response_satisfies_model_boundary() -> None:
    result = OllamaModel().generate(
        ModelRequest(
            instructions="Answer in one short sentence.",
            question="Reply with the word ready.",
        )
    )

    assert isinstance(result, TextResponse)
    assert result.text
    assert result.metadata.model
    assert result.metadata.input_tokens >= 0
    assert result.metadata.output_tokens >= 0
    assert result.metadata.stop_reason
