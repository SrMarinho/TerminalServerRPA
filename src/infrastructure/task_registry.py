from typing import Protocol


class Task(Protocol):
    async def execute(self, params: dict) -> dict: ...


class TaskRegistry:
    _tasks: dict[str, type] = {}
    _discovered: bool = False

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
        # Idempotent: the filesystem scan runs only once per process.
        if cls._discovered:
            return
        import importlib
        import pkgutil

        import src.automation.tasks as pkg

        count = 0
        # walk_packages recurses into subdirectories so the filesystem
        # can mirror the Senior ERP menu hierarchy (e.g.
        # financas/gestao_contas_receber/contas_receber/relatorios/…).
        for _importer, modname, _ispkg in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg.__name__}."):
            importlib.import_module(modname)
            count += 1
        if count == 0:
            importlib.import_module("src.automation.tasks")
        cls._discovered = True

    @classmethod
    def get_schema(cls, name: str) -> list:
        task_cls = cls.get(name)
        if task_cls is None or not hasattr(task_cls, "get_schema"):
            return []
        return task_cls.get_schema()
