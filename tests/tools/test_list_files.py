from pathlib import Path
from archagent.tools.list_files import (
    EntryKind,
    ListEntry,
    ListFilesSuccess,
    ListFilesTool,
)

def test_list_files_returns_sorted_immediate_entries(tmp_path: Path) -> None:
      (tmp_path / "zebra.py").write_text("", encoding="utf-8")

      child_directory = tmp_path / "alpha"
      child_directory.mkdir()
      (child_directory / "nested.py").write_text("", encoding="utf-8")

      tool = ListFilesTool(repository_root=tmp_path)

      result = tool.list_files(".")

      assert result == ListFilesSuccess(
          directory=".",
          entries=(
              ListEntry(path="alpha", kind=EntryKind.DIRECTORY),
              ListEntry(path="zebra.py", kind=EntryKind.FILE),
          ),
      )