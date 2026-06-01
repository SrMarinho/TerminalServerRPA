import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _close_execution_manager():
    """Close the singleton DB connection after each test so SQLite handles
    are released deterministically instead of being GC'd mid-suite."""
    yield
    from src.infrastructure.execution_manager import close_manager

    close_manager()
