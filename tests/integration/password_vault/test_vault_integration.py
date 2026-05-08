import pytest
from src.password_vault.vault import Vault

@pytest.fixture
def vault():
    return Vault()

class TestVaultIntegration:
    def test_roundtrip(self, vault):
        vault.set_password("test-svc", "test-usr", "secret-value")
        assert vault.get_password("test-svc", "test-usr") == "secret-value"
        vault.delete_password("test-svc", "test-usr")
        assert vault.get_password("test-svc", "test-usr") is None

    def test_multiple_services_independent(self, vault):
        vault.set_password("s1", "u1", "p1")
        vault.set_password("s2", "u2", "p2")
        assert vault.get_password("s1", "u1") == "p1"
        assert vault.get_password("s2", "u2") == "p2"

    def test_update_preserves_other_credentials(self, vault):
        vault.set_password("svc", "u1", "p1")
        vault.set_password("svc", "u2", "p2")
        vault.set_password("svc", "u1", "updated")
        creds = vault.list_credentials("svc")
        assert len(creds) == 2
