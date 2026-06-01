from unittest.mock import patch

from src.automation.tasks.report_generation import GeracaoRelatorio


class TestSchema:
    def test_schema_has_core_fields(self):
        names = [f["name"] for f in GeracaoRelatorio.get_schema()]
        assert "base_url" in names
        assert "TS Credenciais" in names
        assert "Senior Credenciais" in names
        assert "relatorio" in names

    def test_relatorio_field_is_a_select(self):
        relatorio = next(f for f in GeracaoRelatorio.get_schema() if f["name"] == "relatorio")
        assert relatorio["type"] == "select"
        assert isinstance(relatorio["options"], list)

    def test_conditional_fields_carry_when_clause(self):
        # report-specific fields are tagged with a `when` so the UI shows them
        # only for the matching report.
        conditional = [f for f in GeracaoRelatorio.get_schema() if "when" in f]
        assert conditional, "expected at least one report-specific field"
        assert all("relatorio" in f["when"] for f in conditional)


class TestSteps:
    def test_three_phases(self):
        steps = GeracaoRelatorio.get_steps()
        assert set(steps) == {"Login", "Processamento", "Finalização"}

    def test_login_phase_steps(self):
        assert GeracaoRelatorio.get_steps()["Login"] == ["Login TS", "Iniciando Senior", "Login Senior"]


class TestResolveCreds:
    def test_resolves_from_vault_when_service_given(self):
        with patch("src.automation.tasks.report_generation.Vault") as mock_vault_cls:
            v = mock_vault_cls.return_value
            v.list_credentials.return_value = [{"username": "u1"}]
            v.get_password.return_value = "secret"
            out = GeracaoRelatorio._resolve_creds({"TS Credenciais": {"service": "svc"}}, "TS Credenciais")
        assert out == {"username": "u1", "password": "secret"}

    def test_empty_password_falls_back_to_blank(self):
        with patch("src.automation.tasks.report_generation.Vault") as mock_vault_cls:
            v = mock_vault_cls.return_value
            v.list_credentials.return_value = [{"username": "u1"}]
            v.get_password.return_value = None
            out = GeracaoRelatorio._resolve_creds({"TS Credenciais": {"service": "svc"}}, "TS Credenciais")
        assert out == {"username": "u1", "password": ""}

    def test_returns_raw_dict_when_no_service(self):
        out = GeracaoRelatorio._resolve_creds({"TS Credenciais": {"username": "x"}}, "TS Credenciais")
        assert out == {"username": "x"}

    def test_returns_empty_for_non_dict(self):
        out = GeracaoRelatorio._resolve_creds({"TS Credenciais": None}, "TS Credenciais")
        assert out == {}

    def test_returns_empty_when_service_has_no_users(self):
        with patch("src.automation.tasks.report_generation.Vault") as mock_vault_cls:
            mock_vault_cls.return_value.list_credentials.return_value = []
            out = GeracaoRelatorio._resolve_creds({"TS Credenciais": {"service": "svc"}}, "TS Credenciais")
        # no users → returns the raw dict unchanged
        assert out == {"service": "svc"}
