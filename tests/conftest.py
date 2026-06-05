import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "plugins"))


@pytest.fixture(autouse=True)
def _close_execution_manager():
    """Close the singleton DB connection after each test so SQLite handles
    are released deterministically instead of being GC'd mid-suite."""
    yield
    from src.infrastructure.execution_manager import close_manager

    close_manager()
