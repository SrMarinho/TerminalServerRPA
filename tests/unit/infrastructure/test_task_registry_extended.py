import pytest

from src.infrastructure.models import TaskInfo
from src.infrastructure.task_registry import TaskRegistry


@pytest.fixture
def clean_registry():
    before = dict(TaskRegistry._tasks)
    yield
    TaskRegistry._tasks.clear()
    TaskRegistry._tasks.update(before)


class TestRegister:
    def test_registers_async_task(self, clean_registry):
        @TaskRegistry.register("mytask")
        class T:
            async def execute(self, params):
                return {}

        assert TaskRegistry.get("mytask") is T

    def test_default_name_from_class(self, clean_registry):
        @TaskRegistry.register()
        class FooTask:
            async def execute(self, params):
                return {}

        assert TaskRegistry.get("foo") is FooTask

    def test_rejects_non_async_execute(self, clean_registry):
        @TaskRegistry.register("sync_bad")
        class Bad:
            def execute(self, params):  # not a coroutine
                return {}

        assert TaskRegistry.get("sync_bad") is None

    def test_rejects_missing_execute(self, clean_registry):
        @TaskRegistry.register("no_exec")
        class NoExec:
            pass

        assert TaskRegistry.get("no_exec") is None


class TestListInfo:
    def test_steps_dict_preserved(self, clean_registry):
        @TaskRegistry.register("with_steps")
        class T:
            async def execute(self, params):
                return {}

            @staticmethod
            def get_steps():
                return {"Phase": ["a", "b"]}

        info = next(i for i in TaskRegistry.list_info() if i.name == "with_steps")
        assert isinstance(info, TaskInfo)
        assert info.steps == {"Phase": ["a", "b"]}

    def test_steps_list_wrapped_in_empty_phase(self, clean_registry):
        @TaskRegistry.register("list_steps")
        class T:
            async def execute(self, params):
                return {}

            @staticmethod
            def get_steps():
                return ["x", "y"]

        info = next(i for i in TaskRegistry.list_info() if i.name == "list_steps")
        assert info.steps == {"": ["x", "y"]}

    def test_display_name_strips_namespace(self, clean_registry):
        TaskRegistry._tasks["plug:inner"] = type("X", (), {"execute": staticmethod(lambda self, p: {})})
        info = next(i for i in TaskRegistry.list_info() if i.name == "plug:inner")
        assert info.display_name == "inner"


class TestUnregisterPlugin:
    def test_removes_only_matching_prefix(self, clean_registry):
        TaskRegistry._tasks["plugA:one"] = object
        TaskRegistry._tasks["plugA:two"] = object
        TaskRegistry._tasks["plugB:three"] = object
        TaskRegistry.unregister_plugin("plugA")
        remaining = set(TaskRegistry._tasks)
        assert "plugA:one" not in remaining
        assert "plugA:two" not in remaining
        assert "plugB:three" in remaining


class TestGetSchema:
    def test_returns_schema(self, clean_registry):
        @TaskRegistry.register("with_schema")
        class T:
            async def execute(self, params):
                return {}

            @staticmethod
            def get_schema():
                return [{"name": "f", "type": "string"}]

        assert TaskRegistry.get_schema("with_schema") == [{"name": "f", "type": "string"}]

    def test_missing_task_returns_empty(self, clean_registry):
        assert TaskRegistry.get_schema("ghost") == []

    def test_task_without_schema_returns_empty(self, clean_registry):
        @TaskRegistry.register("no_schema")
        class T:
            async def execute(self, params):
                return {}

        assert TaskRegistry.get_schema("no_schema") == []
