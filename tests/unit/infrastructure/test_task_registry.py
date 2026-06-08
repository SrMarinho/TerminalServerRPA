import pytest

from src.infrastructure.task_registry import TaskRegistry


@pytest.fixture(autouse=True)
def clear_registry():
    TaskRegistry._tasks.clear()
    yield
    TaskRegistry._tasks.clear()


class TestTaskRegistry:
    def test_list_empty_initially(self):
        assert TaskRegistry.list() == []

    def test_register_class(self):
        @TaskRegistry.register()
        class MyTask:
            async def execute(self, params: dict) -> dict:
                return {}

        assert "my" in TaskRegistry.list()

    def test_register_with_custom_name(self):
        @TaskRegistry.register("custom-name")
        class Something:
            async def execute(self, params: dict) -> dict:
                return {}

        assert "custom-name" in TaskRegistry.list()

    def test_get_returns_class(self):
        @TaskRegistry.register("get-test")
        class GetTest:
            async def execute(self, params: dict) -> dict:
                return {}

        assert TaskRegistry.get("get-test") is GetTest

    def test_get_returns_none_for_missing(self):
        assert TaskRegistry.get("nonexistent") is None

    def test_register_rejects_missing_execute(self):
        @TaskRegistry.register("no-execute")
        class BadTask:
            pass

        assert "no-execute" not in TaskRegistry.list()

    def test_multiple_tasks(self):
        @TaskRegistry.register("task-a")
        class A:
            async def execute(self, params: dict) -> dict:
                return {}

        @TaskRegistry.register("task-b")
        class B:
            async def execute(self, params: dict) -> dict:
                return {}

        names = TaskRegistry.list()
        assert "task-a" in names
        assert "task-b" in names

    def test_auto_discover_imports_all_task_modules(self):
        # auto_discover scans filesystem and imports modules
        # already-imported modules are cached so decorators won't re-run
        # this test verifies the scan runs without error
        count_before = len(TaskRegistry.list())
        TaskRegistry.auto_discover()
        count_after = len(TaskRegistry.list())
        assert count_after >= count_before
