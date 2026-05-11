from unittest.mock import MagicMock, patch

import click
import pytest
from typer.testing import CliRunner

runner = CliRunner()


class TestCliRun:
    def test_run_function_calls_runner(self):
        from src.interfaces.cli.cli import run
        async def fake_run(*a, **kw):
            pass
        mock_runner = MagicMock()
        mock_runner.run = fake_run
        mock_runner.status.value = "completed"
        with patch("src.infrastructure.task_runner.TaskRunner", return_value=mock_runner):
            run("test-task")


class TestCliLogs:
    def test_logs_missing_file_exits(self, tmp_path):
        import os

        from src.interfaces.cli.cli import logs
        orig_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        with patch("typer.echo"), pytest.raises(click.exceptions.Exit):
            logs()
        os.chdir(orig_cwd)

    @staticmethod
    def _make_log_file_mock(lines):
        mock_file = MagicMock()
        mock_file.readlines.return_value = lines
        mock_file.__enter__.return_value = mock_file
        return mock_file

    def test_logs_filters_by_level(self):
        from src.interfaces.cli.cli import Path as CliPath
        from src.interfaces.cli.cli import logs
        mock_file = self._make_log_file_mock([
            '{"timestamp": "2026-01-01T12:00:00Z", "level": "info", "event": "test event"}\n',
            '{"timestamp": "2026-01-01T12:01:00Z", "level": "error", "event": "error event"}\n',
        ])
        with (
            patch.object(CliPath, "exists", return_value=True),
            patch.object(CliPath, "open", return_value=mock_file),
            patch("typer.echo") as mock_echo,
        ):
            logs(level="error")
            calls = [c[0][0] for c in mock_echo.call_args_list if "error" in c[0][0].lower()]
            assert len(calls) >= 1

    def test_logs_json_output(self):
        from src.interfaces.cli.cli import Path as CliPath
        from src.interfaces.cli.cli import logs
        mock_file = self._make_log_file_mock([
            '{"timestamp": "2026-01-01T12:00:00Z", "level": "info", "event": "test"}\n',
        ])
        with (
            patch.object(CliPath, "exists", return_value=True),
            patch.object(CliPath, "open", return_value=mock_file),
            patch("typer.echo") as mock_echo,
        ):
            logs(json=True)
            assert any('"event": "test"' in c[0][0] for c in mock_echo.call_args_list)

    def test_logs_skips_invalid_json(self):
        from src.interfaces.cli.cli import Path as CliPath
        from src.interfaces.cli.cli import logs
        mock_file = self._make_log_file_mock([
            'not valid json\n',
            '{"timestamp": "2026-01-01T12:00:00Z", "level": "info", "event": "ok"}\n',
        ])
        with (
            patch.object(CliPath, "exists", return_value=True),
            patch.object(CliPath, "open", return_value=mock_file),
            patch("typer.echo") as mock_echo,
        ):
            logs()
            assert any('ok' in c[0][0] for c in mock_echo.call_args_list)

    def test_logs_filters_by_task(self):
        from src.interfaces.cli.cli import Path as CliPath
        from src.interfaces.cli.cli import logs
        mock_file = self._make_log_file_mock([
            '{"timestamp": "2026-01-01T12:00:00Z", "level": "info", "event": "a", "task": "t1"}\n',
            '{"timestamp": "2026-01-01T12:01:00Z", "level": "info", "event": "b", "task": "t2"}\n',
        ])
        with (
            patch.object(CliPath, "exists", return_value=True),
            patch.object(CliPath, "open", return_value=mock_file),
            patch("typer.echo") as mock_echo,
        ):
            logs(task="t1")
            has_a = any('"a"' in c[0][0] or 'a' in c[0][0] for c in mock_echo.call_args_list)
            has_b = any('"b"' in c[0][0] or (
                isinstance(c[0][0], str) and c[0][0].endswith("b")
            ) for c in mock_echo.call_args_list)
            assert has_a
            assert not has_b
