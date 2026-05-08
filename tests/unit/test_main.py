from unittest.mock import patch

from typer.testing import CliRunner

runner = CliRunner()


class TestMainWeb:
    @patch("src.interfaces.web.server.run_server")
    def test_web_command(self, mock_run_server):
        from main import app
        result = runner.invoke(app, ["web", "--port", "9090", "--no-browser"])
        assert result.exit_code == 0
        mock_run_server.assert_called_once_with(port=9090, open_browser=False)

    @patch("src.interfaces.web.server.run_server")
    def test_web_defaults(self, mock_run_server):
        from main import app
        result = runner.invoke(app, ["web"])
        assert result.exit_code == 0
        mock_run_server.assert_called_once_with(port=8080, open_browser=True)


class TestMainVault:
    @patch("src.interfaces.cli.cli.vault_app")
    def test_vault_command(self, mock_vault_app):
        from main import app
        result = runner.invoke(app, ["vault", "--help"])
        assert result.exit_code == 0


class TestMainRun:
    @patch("src.interfaces.cli.cli.run")
    def test_run_command(self, mock_run):
        from main import app
        result = runner.invoke(app, ["run", "bulk-register-users"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with("bulk-register-users")


class TestMainLogs:
    @patch("src.interfaces.cli.cli.logs")
    def test_logs_command(self, mock_logs):
        from main import app
        result = runner.invoke(app, ["logs", "--level", "error"])
        assert result.exit_code == 0
        mock_logs.assert_called_once_with("error", "", "", False)
