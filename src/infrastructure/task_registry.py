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
        import importlib
        import pkgutil

        import src.automation.tasks as pkg
        count = 0
        for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"src.automation.tasks.{modname}")
            count += 1
        if count == 0:
            importlib.import_module("src.automation.tasks")

    @classmethod
    def get_schema(cls, name: str) -> list:
        task_cls = cls.get(name)
        if task_cls is None or not hasattr(task_cls, "get_schema"):
            return []
        return task_cls.get_schema()
