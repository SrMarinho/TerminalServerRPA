from unittest.mock import patch

from typer.testing import CliRunner

from src.infrastructure.vault import Vault

runner = CliRunner()

class TestE2EVault:
    @patch("src.interfaces.cli.cli.Vault", wraps=Vault)
    def test_cli_set_get_delete_flow(self, mock_vault_cls):
        import src.interfaces.cli.cli as cli_mod
        cli_mod._vault = None
        v = Vault()
        mock_vault_cls.return_value = v

        runner.invoke(cli_mod.vault_app, ["set", "e2e-svc", "-u", "e2e-usr"], input="e2e-secret\n")
        result = runner.invoke(cli_mod.vault_app, ["get", "e2e-svc", "-u", "e2e-usr"])
        assert result.exit_code == 0
        assert "e2e-secret" in result.stdout

        result = runner.invoke(cli_mod.vault_app, ["delete", "e2e-svc"])
        assert result.exit_code == 0
        result = runner.invoke(cli_mod.vault_app, ["get", "e2e-svc", "-u", "e2e-usr"])
        assert result.exit_code == 1
