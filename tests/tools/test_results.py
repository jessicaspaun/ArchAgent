from dataclasses import FrozenInstanceError

import pytest

from archagent.tools.results import ToolFailure


def test_tool_failure_stores_code_and_message() -> None:
    failure = ToolFailure(
        code="outside_repository",
        message="The requested path is outside the repository",
    )

    assert failure.code == "outside_repository"
    assert failure.message == "The requested path is outside the repository"


def test_tool_failure_is_immutable() -> None:
    failure = ToolFailure(
        code="outside_repository",
        message="The requested path is outside the repository",
    )

    with pytest.raises(FrozenInstanceError):
        failure.code = "direcotry_not_found"
