from io import StringIO
from pathlib import Path
from typing import TextIO

import pytest

import archagent.run_log as log_module
from archagent.run_log import RunLog, RunLogError


@pytest.mark.parametrize("operation", ["write", "flush", "close"])
def test_run_log_translates_stream_io_failures(
    logs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    class FailingStream(StringIO):
        def write(self, text: str) -> int:
            if operation == "write":
                raise OSError("secret write details")
            return super().write(text)

        def flush(self) -> None:
            if operation == "flush":
                raise OSError("secret flush details")
            super().flush()

        def close(self) -> None:
            if operation == "close":
                super().close()
                raise OSError("secret close details")
            super().close()

    stream = FailingStream()

    def opened(self: Path, mode: str, encoding: str) -> TextIO:
        assert mode == "x"
        assert encoding == "utf-8"
        return stream

    monkeypatch.setattr(Path, "open", opened)

    with pytest.raises(RunLogError) as captured:
        with RunLog(logs_dir, None) as log:
            log.write("example", {"value": "content"})

    assert "secret" not in str(captured.value)
    assert stream.closed


def test_run_log_flushes_each_record_before_continuing(logs_dir: Path) -> None:
    with RunLog(logs_dir, None) as log:
        log.write("example", {"value": "complete"})
        path = next(logs_dir.glob("*.jsonl"))
        assert '"complete"' in path.read_text(encoding="utf-8")


def test_log_filename_collision_never_overwrites_existing_records(
    logs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedUuid:
        hex = "a" * 32

    monkeypatch.setattr(log_module, "uuid4", lambda: FixedUuid())
    logs_dir.mkdir()
    existing = logs_dir / ("a" * 32 + ".jsonl")
    existing.write_text("previous run", encoding="utf-8")

    with pytest.raises(RunLogError, match="could not be created"):
        RunLog(logs_dir, None)

    assert existing.read_text(encoding="utf-8") == "previous run"


@pytest.mark.parametrize("through_symlink", [False, True])
def test_run_log_rejects_directories_inside_the_target_before_writing(
    tmp_path: Path,
    through_symlink: bool,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    directory = target / "logs"
    if through_symlink:
        directory = tmp_path / "alias"
        directory.symlink_to(target, target_is_directory=True)

    with pytest.raises(RunLogError, match="outside the target repository"):
        RunLog(directory, target)

    assert list(target.iterdir()) == []


def test_log_close_failure_does_not_mask_an_existing_exception(
    logs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BadClose(StringIO):
        def close(self) -> None:
            super().close()
            raise OSError("Cannot close stream")

    stream = BadClose()

    def opened(self: Path, mode: str, encoding: str) -> TextIO:
        return stream

    monkeypatch.setattr(Path, "open", opened)

    with pytest.raises(RuntimeError, match="Original defect"):
        with RunLog(logs_dir, None):
            raise RuntimeError("Original defect")

    assert stream.closed


def test_log_serialization_defects_propagate(logs_dir: Path) -> None:
    with pytest.raises(TypeError):
        with RunLog(logs_dir, None) as log:
            log.write("example", {"value": object()})
