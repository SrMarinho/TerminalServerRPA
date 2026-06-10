import sys

import pytest

from src.infrastructure import plugin_loader as pl
from src.infrastructure.plugin_loader import _parse_version, _read_manifest, load_plugins, reload_plugins
from src.infrastructure.task_registry import TaskRegistry

_PLUGIN_INIT = """\
from src.infrastructure.task_registry import TaskRegistry


@TaskRegistry.register("greet")
class GreetTask:
    async def execute(self, params: dict) -> dict:
        return {"hi": True}
"""


def _make_plugin(root, name, *, toml: str | None = None, init: str = _PLUGIN_INIT):
    d = root / name
    d.mkdir()
    (d / "__init__.py").write_text(init, encoding="utf-8")
    if toml is not None:
        (d / "plugin.toml").write_text(toml, encoding="utf-8")
    return d


@pytest.fixture
def isolate(monkeypatch):
    """Snapshot sys.path / sys.modules / registry so plugin loading can't leak."""
    path_before = list(sys.path)
    tasks_before = dict(TaskRegistry._tasks)
    mods_before = set(sys.modules)
    yield
    sys.path[:] = path_before
    TaskRegistry._tasks.clear()
    TaskRegistry._tasks.update(tasks_before)
    for m in set(sys.modules) - mods_before:
        del sys.modules[m]


class TestParseVersion:
    def test_simple(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_strips_non_digits(self):
        assert _parse_version("1.2.3rc1") == (1, 2, 31)

    def test_empty_chunk_is_zero(self):
        assert _parse_version("1..3") == (1, 0, 3)

    def test_comparable(self):
        assert _parse_version("0.9.0") < _parse_version("1.0.0")


class TestReadManifest:
    def test_missing_returns_none(self, tmp_path):
        assert _read_manifest(tmp_path) is None

    def test_parses_plugin_table(self, tmp_path):
        (tmp_path / "plugin.toml").write_text(
            '[plugin]\nname = "myplug"\nmin_app_version = "1.0.0"\n', encoding="utf-8"
        )
        manifest = _read_manifest(tmp_path)
        assert manifest == {"name": "myplug", "min_app_version": "1.0.0"}


class TestScanLoad:
    def test_loads_and_namespaces_task(self, tmp_path, isolate, monkeypatch):
        _make_plugin(tmp_path, "alpha_plugin")
        monkeypatch.setattr("src.config.settings.PLUGINS_DIRS", [tmp_path])
        load_plugins()
        assert "alpha_plugin:greet" in TaskRegistry._tasks

    def test_manifest_name_used_for_namespace(self, tmp_path, isolate, monkeypatch):
        _make_plugin(tmp_path, "dir_name", toml='[plugin]\nname = "branded"\n')
        monkeypatch.setattr("src.config.settings.PLUGINS_DIRS", [tmp_path])
        load_plugins()
        assert "branded:greet" in TaskRegistry._tasks

    def test_skips_incompatible_version(self, tmp_path, isolate, monkeypatch):
        _make_plugin(tmp_path, "future_plugin", toml='[plugin]\nmin_app_version = "999.0.0"\n')
        monkeypatch.setattr("src.config.settings.PLUGINS_DIRS", [tmp_path])
        monkeypatch.setattr(pl, "VERSION", "1.0.0", raising=False)
        load_plugins()
        assert not any(k.endswith(":greet") for k in TaskRegistry._tasks)

    def test_skips_non_package_dirs(self, tmp_path, isolate, monkeypatch):
        (tmp_path / "not_a_pkg").mkdir()  # no __init__.py
        monkeypatch.setattr("src.config.settings.PLUGINS_DIRS", [tmp_path])
        load_plugins()  # must not raise

    def test_load_failure_is_isolated(self, tmp_path, isolate, monkeypatch):
        _make_plugin(tmp_path, "broken_plugin", init="raise RuntimeError('boom on import')\n")
        _make_plugin(tmp_path, "good_plugin")
        monkeypatch.setattr("src.config.settings.PLUGINS_DIRS", [tmp_path])
        load_plugins()
        # broken one is skipped, good one still loads
        assert "good_plugin:greet" in TaskRegistry._tasks

    def test_creates_missing_dir(self, tmp_path, isolate):
        target = tmp_path / "made_on_demand"
        pl._scan_dir(target)
        assert target.exists()


class TestReload:
    def test_reload_unregisters_then_rescans(self, tmp_path, isolate, monkeypatch):
        _make_plugin(tmp_path, "reloadable")
        monkeypatch.setattr("src.config.settings.PLUGINS_DIRS", [tmp_path])
        load_plugins()
        assert "reloadable:greet" in TaskRegistry._tasks

        names = reload_plugins()
        assert "reloadable" in names
        assert "reloadable:greet" in TaskRegistry._tasks  # re-registered after reload
        # module was purged + reimported
        assert "reloadable" in sys.modules
