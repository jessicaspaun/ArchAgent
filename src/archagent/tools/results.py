from dataclasses import dataclass


@dataclass(frozen=True)
class ToolFailure:
    code: str
    message: str
