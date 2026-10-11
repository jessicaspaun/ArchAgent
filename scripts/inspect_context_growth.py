"""Show request growth and a run log without calling a live model.

Run from the project root:
    PYTHONPATH=src uv run python scripts/inspect_context_growth.py
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.request import Request

from archagent.agent import AgentHarness, AgentSuccess
from archagent.ollama import OllamaModel
from archagent.tools.registry import create_repository_registry


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    logs_dir = project_root / "logs"
    previous_logs = set(logs_dir.glob("*.jsonl"))
    responses = iter(
        [
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "list",
                        "function": {
                            "name": "list_files",
                            "arguments": {"path": "."},
                        },
                    }
                ],
            },
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "read",
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": "app.py"},
                        },
                    }
                ],
            },
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "search",
                        "function": {
                            "name": "search_code",
                            "arguments": {"path": ".", "query": "state"},
                        },
                    }
                ],
            },
            {"content": "The fixture defines state in app.py."},
        ]
    )
    sizes: list[tuple[int, int, int]] = []

    @contextmanager
    def fake_urlopen(request: Request, timeout: float) -> Iterator[BytesIO]:
        assert isinstance(request.data, bytes)
        messages = json.loads(request.data)["messages"]
        sizes.append((len(sizes) + 1, len(messages), len(request.data)))
        response = {
            "model": "deterministic-fixture",
            "message": next(responses),
            "done_reason": "stop",
            "prompt_eval_count": 1,
            "eval_count": 1,
        }
        with BytesIO(json.dumps(response).encode("utf-8")) as stream:
            yield stream

    with TemporaryDirectory(prefix="archagent-context-") as temporary:
        target = Path(temporary)
        (target / "app.py").write_text("state = {}\n# λ\n", encoding="utf-8")
        registry = create_repository_registry(target, project_root)
        harness = AgentHarness(
            OllamaModel(), registry, "Inspect repository data.", logs_dir=logs_dir
        )
        with patch("archagent.ollama.urlopen", fake_urlopen):
            outcome = harness.run("Where is state defined?")
        assert isinstance(outcome, AgentSuccess)

    print("Model round | Messages | Encoded request bytes")
    for round_number, messages_count, byte_count in sizes:
        print(f"{round_number:11} | {messages_count:8} | {byte_count:21}")
    print("These are JSON body bytes, not model tokens.")
    print("No live model was called; the scripted answer does not evaluate AI quality.")
    for path in sorted(set(logs_dir.glob("*.jsonl")) - previous_logs):
        print(f"Run log: {path}")


if __name__ == "__main__":
    main()
