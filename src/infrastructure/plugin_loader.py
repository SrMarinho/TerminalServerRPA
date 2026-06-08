import importlib
import sys
from pathlib import Path

from src.infrastructure.logger import get_logger

log = get_logger("TerminalServerRPA.plugins")


def _parse_version(v: str) -> tuple[int, ...]:
    parts = []
    for chunk in v.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _read_manifest(plugin_dir: Path) -> dict | None:
    toml_path = plugin_dir / "plugin.toml"
    if not toml_path.exists():
        return None
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            log.warning("plugin.toml_skipped", name=plugin_dir.name, reason="tomllib/tomli not available")
            return None
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    return data.get("plugin", {})


def _scan_dir(plugins_dir: Path) -> None:
    if not plugins_dir.exists():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return

    from src.config.version import VERSION
    from src.infrastructure.task_registry import TaskRegistry

    root = str(plugins_dir)
    if root not in sys.path:
        sys.path.insert(0, root)

    for entry in plugins_dir.iterdir():
        if not entry.is_dir() or not (entry / "__init__.py").exists():
            continue

        manifest = _read_manifest(entry)
        if manifest:
            min_ver = manifest.get("min_app_version", "0.0.0")
            if _parse_version(VERSION) < _parse_version(min_ver):
                log.warning(
                    "plugin.incompatible",
                    name=entry.name,
                    requires=min_ver,
                    app=VERSION,
                )
                continue

        before = set(TaskRegistry._tasks.keys())
        try:
            importlib.import_module(entry.name)
            log.info("plugin.loaded", name=entry.name)
        except Exception:
            log.exception("plugin.load_failed", name=entry.name)
            continue

        # Namespace newly-registered task names with the plugin dir name
        # to avoid collisions when multiple plugins register tasks.
        new_keys = set(TaskRegistry._tasks.keys()) - before
        plugin_name = (manifest or {}).get("name", entry.name)
        for key in new_keys:
            namespaced = f"{plugin_name}:{key}"
            TaskRegistry._tasks[namespaced] = TaskRegistry._tasks.pop(key)
            log.debug("plugin.task_registered", original=key, namespaced=namespaced)


def load_plugins() -> None:
    from src.config.settings import PLUGINS_DIRS

    for d in PLUGINS_DIRS:
        _scan_dir(d)
