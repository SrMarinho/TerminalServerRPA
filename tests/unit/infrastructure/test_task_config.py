import json
from unittest.mock import patch

import pytest

from src.infrastructure.task_config import load_config, save_config


class TestTaskConfig:
    @pytest.fixture
    def isolated_dir(self, tmp_path):
        with patch("src.infrastructure.task_config.TASKS_DIR", tmp_path / ".local" / "tasks"):
            yield

    def test_load_empty_when_missing(self, isolated_dir):
        assert load_config("test-task") == {}

    def test_save_and_load_roundtrip(self, isolated_dir):
        params = {"base_url": "http://example.com", "users": ["u1", "u2"]}
        save_config("roundtrip-task", params)
        loaded = load_config("roundtrip-task")
        assert loaded == params

    def test_overwrites_existing(self, isolated_dir):
        save_config("overwrite-task", {"version": 1})
        save_config("overwrite-task", {"version": 2})
        assert load_config("overwrite-task") == {"version": 2}

    def test_tasks_are_independent(self, isolated_dir):
        save_config("task-a", {"name": "A"})
        save_config("task-b", {"name": "B"})
        assert load_config("task-a") == {"name": "A"}
        assert load_config("task-b") == {"name": "B"}

    def test_invalid_json_raises(self, isolated_dir):
        from src.infrastructure.task_config import TASKS_DIR
        bad = TASKS_DIR / "bad.json"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_config("bad")
