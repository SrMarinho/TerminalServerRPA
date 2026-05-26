import json
from pathlib import Path

TASKS_DIR = Path(".local") / "tasks"


def _ensure_dir():
    TASKS_DIR.mkdir(parents=True, exist_ok=True)


def _path(task_name: str) -> Path:
    return TASKS_DIR / f"{task_name}.json"


def load_config(task_name: str) -> dict:
    p = _path(task_name)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_config(task_name: str, params: dict):
    _ensure_dir()
    _path(task_name).write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
