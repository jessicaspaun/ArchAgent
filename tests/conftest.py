from pathlib import Path

import pytest


@pytest.fixture
def logs_dir(tmp_path: Path) -> Path:
    """Each harness test owns logs outside its target-repository fixture."""
    return tmp_path / "logs"
