import json
from contextlib import suppress

import keyring
from cryptography.fernet import Fernet
from keyring.errors import PasswordDeleteError

_INDEX_SERVICE = "TerminalServerRPA-index"
_INDEX_USER = "_service_index"
_KEY_SERVICE = "TerminalServerRPA"
_KEY_USER = "_vault_key"


class Vault:
    def __init__(self):
        self._key = self._get_or_create_key()
        self._fernet = Fernet(self._key)

    def _get_or_create_key(self) -> bytes:
        raw = keyring.get_password(_KEY_SERVICE, _KEY_USER)
        if raw:
            return raw.encode() if isinstance(raw, str) else raw
        key = Fernet.generate_key()
        keyring.set_password(_KEY_SERVICE, _KEY_USER, key.decode())
        return key

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            raise ValueError(f"decrypt failed: {e}") from e

    def _load_index(self) -> dict:
        raw = keyring.get_password(_INDEX_SERVICE, _INDEX_USER)
        if not raw:
            return {}
        return json.loads(self._decrypt(raw))

    def _save_index(self, index: dict):
        raw = self._encrypt(json.dumps(index))
        keyring.set_password(_INDEX_SERVICE, _INDEX_USER, raw)

    def _add_to_index(self, service: str, username: str):
        idx = self._load_index()
        users = idx.setdefault(service, [])
        if username not in users:
            users.append(username)
        self._save_index(idx)

    def _remove_from_index(self, service: str, username: str | None = None):
        idx = self._load_index()
        if service not in idx:
            return
        if username is None:
            del idx[service]
        else:
            idx[service] = [u for u in idx[service] if u != username]
            if not idx[service]:
                del idx[service]
        self._save_index(idx)

    def set_password(self, service: str, username: str, password: str):
        encrypted = self._encrypt(password)
        keyring.set_password(service, username, encrypted)
        self._add_to_index(service, username)

    def get_password(self, service: str, username: str) -> str | None:
        encrypted = keyring.get_password(service, username)
        if not encrypted:
            return None
        return self._decrypt(encrypted)

    def delete_password(self, service: str, username: str | None = None):
        if username:
            keyring.delete_password(service, username)
            self._remove_from_index(service, username)
        else:
            creds = self.list_credentials(service)
            for c in creds:
                with suppress(PasswordDeleteError):
                    keyring.delete_password(service, c["username"])
            self._remove_from_index(service)

    def list_services(self) -> list:
        return list(self._load_index().keys())

    def list_credentials(self, service: str) -> list:
        idx = self._load_index()
        return [{"username": u} for u in idx.get(service, [])]
