import importlib
import pkgutil
from typing import Protocol


class Task(Protocol):
    async def execute(self, params: dict) -> dict: ...


class TaskRegistry:
    _tasks: dict[str, type] = {}

    @classmethod
    def register(cls, name: str = ""):
        def decorator(task_cls: type):
            task_name = name or task_cls.__name__.replace("Task", "").lower()
            cls._tasks[task_name] = task_cls
            return task_cls
        return decorator

    @classmethod
    def get(cls, name: str) -> type | None:
        return cls._tasks.get(name)

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._tasks.keys())

    @classmethod
    def auto_discover(cls):
        import src.automation.tasks as pkg
        for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"src.automation.tasks.{modname}")
