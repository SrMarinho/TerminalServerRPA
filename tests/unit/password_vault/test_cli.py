import pytest
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner
from src.password_vault.cli import vault_app
from src.password_vault.vault import Vault

runner = CliRunner()

@pytest.fixture(autouse=True)
def mock_vault():
    import src.password_vault.cli as cli_mod
    cli_mod._vault = None
    m = MagicMock(spec=Vault)
    m.get_password.return_value = None
    m.list_services.return_value = []
    m.list_credentials.return_value = []
    with patch("src.password_vault.cli.Vault", return_value=m):
        yield m

class TestCliSet:
    def test_set_password_prompts_for_secret(self, mock_vault):
        result = runner.invoke(vault_app, ["set", "svc", "-u", "usr"], input="secret123\n")
        assert result.exit_code == 0
        mock_vault.set_password.assert_called_once_with("svc", "usr", "secret123")

    def test_set_password_without_username(self, mock_vault):
        result = runner.invoke(vault_app, ["set", "svc"], input="secret123\n")
        assert result.exit_code != 0

class TestCliGet:
    def test_get_password(self, mock_vault):
        mock_vault.get_password.return_value = "mypass"
        result = runner.invoke(vault_app, ["get", "svc", "-u", "usr"])
        assert result.exit_code == 0
        assert "mypass" in result.stdout

    def test_get_password_not_found(self, mock_vault):
        mock_vault.get_password.return_value = None
        result = runner.invoke(vault_app, ["get", "svc", "-u", "usr"])
        assert result.exit_code == 1

class TestCliDelete:
    def test_delete_credential(self, mock_vault):
        result = runner.invoke(vault_app, ["delete", "svc"])
        assert result.exit_code == 0
        mock_vault.delete_password.assert_called_once_with("svc")

class TestCliList:
    def test_list_empty(self, mock_vault):
        result = runner.invoke(vault_app, ["list"])
        assert result.exit_code == 0

    def test_list_with_services(self, mock_vault):
        mock_vault.list_services.return_value = ["svc1", "svc2"]
        mock_vault.list_credentials.side_effect = lambda s: [{"username": "usr1"}] if s == "svc1" else [{"username": "usr2"}]
        result = runner.invoke(vault_app, ["list"])
        assert result.exit_code == 0
        assert "svc1" in result.stdout
        assert "svc2" in result.stdout
