from unittest.mock import patch

import pytest
from keyring.errors import PasswordDeleteError

from src.infrastructure.vault import Vault


@pytest.fixture(autouse=True)
def mock_keyring():
    store = {}
    with patch("src.infrastructure.vault.keyring") as mock:
        mock.get_password.side_effect = lambda s, u: store.get((s, u))
        mock.set_password.side_effect = lambda s, u, p: store.update({(s, u): p})
        mock.delete_password.side_effect = lambda s, u: store.pop((s, u), None)
        yield mock, store

_VALID_KEY = "uVWUI9F8u2aRkt5hbgD_LaolVcVveOLZGNDKpajdI1k="

@pytest.fixture
def vault(mock_keyring):
    _, store = mock_keyring
    store[("senior-rpa", "_vault_key")] = _VALID_KEY
    return Vault()

class TestVaultInit:
    def test_generates_key_on_first_access(self, mock_keyring):
        mock, store = mock_keyring
        store.clear()
        v = Vault()
        assert v._key is not None
        assert store[("senior-rpa", "_vault_key")] is not None

    def test_reuses_existing_key(self, vault):
        k1 = vault._key
        v2 = Vault()
        assert v2._key == k1

class TestVaultSetPassword:
    def test_stores_encrypted_password(self, vault, mock_keyring):
        _, store = mock_keyring
        vault.set_password("svc", "usr", "secret123")
        stored = store.get(("svc", "usr"))
        assert stored is not None
        assert stored != "secret123"

    def test_overwrites_existing(self, vault):
        vault.set_password("svc", "usr", "first")
        vault.set_password("svc", "usr", "second")
        assert vault.get_password("svc", "usr") == "second"

class TestVaultGetPassword:
    def test_returns_password(self, vault):
        vault.set_password("svc", "usr", "mypassword")
        assert vault.get_password("svc", "usr") == "mypassword"

    def test_returns_none_if_not_found(self, vault):
        assert vault.get_password("nonexistent", "usr") is None

    def test_raises_on_decrypt_failure(self, vault, mock_keyring):
        _, store = mock_keyring
        store[("svc", "usr")] = "invalid-ciphertext"
        with pytest.raises(ValueError, match="decrypt"):
            vault.get_password("svc", "usr")

class TestVaultDeletePassword:
    def test_deletes_credential(self, vault):
        vault.set_password("svc", "usr", "pw")
        vault.delete_password("svc", "usr")
        assert vault.get_password("svc", "usr") is None

    def test_delete_nonexistent_does_not_raise(self, vault):
        vault.delete_password("ghost", "usr")

    def test_delete_service_bulk(self, vault):
        vault.set_password("svc", "u1", "p1")
        vault.set_password("svc", "u2", "p2")
        vault.delete_password("svc")
        assert vault.get_password("svc", "u1") is None
        assert vault.get_password("svc", "u2") is None
        assert vault.list_services() == []

    def test_delete_service_bulk_nonexistent(self, vault):
        vault.delete_password("ghost")

    def test_delete_service_bulk_ignores_delete_errors(self, vault, mock_keyring):
        mock, store = mock_keyring
        vault.set_password("svc", "good", "p1")
        vault.set_password("svc", "bad", "p2")

        original_delete = mock.delete_password.side_effect
        def delete_with_error(s, u):
            if u == "bad":
                raise PasswordDeleteError("denied")
            return original_delete(s, u)
        mock.delete_password.side_effect = delete_with_error

        vault.delete_password("svc")
        assert vault.get_password("svc", "good") is None
        assert vault.list_services() == []

class TestVaultListServices:
    def test_lists_all_services(self, vault):
        vault.set_password("svc1", "u1", "p1")
        vault.set_password("svc2", "u2", "p2")
        vault.set_password("svc1", "u3", "p3")
        services = vault.list_services()
        assert "svc1" in services
        assert "svc2" in services

    def test_empty_when_no_credentials(self, vault):
        assert vault.list_services() == []

class TestVaultListCredentials:
    def test_lists_credentials_for_service(self, vault):
        vault.set_password("svc", "u1", "p1")
        vault.set_password("svc", "u2", "p2")
        creds = vault.list_credentials("svc")
        assert len(creds) == 2
        assert {"username": "u1"} in creds
        assert {"username": "u2"} in creds

    def test_returns_empty_for_missing_service(self, vault):
        assert vault.list_credentials("ghost") == []
