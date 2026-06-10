import tomllib
from pathlib import Path

import src.config.version as ver
from src.config.version import VERSION, _load_version

_REPO_ROOT = Path(__file__).resolve().parents[3]


class TestVersion:
    def test_version_is_nonempty_string(self):
        assert isinstance(VERSION, str)
        assert VERSION

    def test_metadata_path_wins(self, monkeypatch):
        monkeypatch.setattr("importlib.metadata.version", lambda _name: "9.9.9")
        assert _load_version() == "9.9.9"

    def test_falls_back_to_source_pyproject(self, monkeypatch):
        def _raise(_name):
            raise RuntimeError("not installed")

        monkeypatch.setattr("importlib.metadata.version", _raise)
        with (_REPO_ROOT / "pyproject.toml").open("rb") as f:
            expected = tomllib.load(f)["project"]["version"]
        assert _load_version() == expected

    def test_hardcoded_fallback_when_nothing_resolves(self, monkeypatch):
        monkeypatch.setattr("importlib.metadata.version", lambda _n: (_ for _ in ()).throw(RuntimeError()))
        monkeypatch.setattr(ver.Path, "exists", lambda self: False)
        assert _load_version() == "0.0.0-dev"
