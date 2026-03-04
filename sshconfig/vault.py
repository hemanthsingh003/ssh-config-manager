import base64
import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


def _get_default_key() -> str:
    import uuid
    machine_id = str(uuid.getnode())
    return f"ssh-config-manager-{machine_id}"


class PasswordVault:
    VAULT_PATH = Path.home() / ".ssh" / "ssh_config_vault"
    SALT_PATH = Path.home() / ".ssh" / ".ssh_config_vault_salt"
    VERIFY_PATH = Path.home() / ".ssh" / ".ssh_config_vault_verify"

    def __init__(self, master_password: Optional[str] = None):
        self._fernet: Optional[Fernet] = None
        self._auto_unlock = False
        if master_password:
            self._initialize(master_password)
        else:
            self._try_auto_unlock()

    def _try_auto_unlock(self) -> bool:
        default_pass = _get_default_key()
        if self.VAULT_PATH.exists() and self.SALT_PATH.exists() and self.VERIFY_PATH.exists():
            if self._verify_master_password(default_pass):
                self._auto_unlock = True
                return True
        else:
            self._create_vault(default_pass)
            self._auto_unlock = True
            return True
        return False

    def _initialize(self, master_password: str) -> None:
        if self.VAULT_PATH.exists() and self.SALT_PATH.exists() and self.VERIFY_PATH.exists():
            self._verify_master_password(master_password)
        else:
            self._create_vault(master_password)

    def _create_vault(self, master_password: str) -> None:
        salt = os.urandom(16)
        self.SALT_PATH.write_bytes(salt)

        key = self._derive_key(master_password, salt)
        fernet = Fernet(key)
        self._fernet = fernet

        self.VAULT_PATH.write_text(json.dumps({}))
        self._save_verification_token(master_password, salt)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)

    def _save_verification_token(self, master_password: str, salt: bytes) -> None:
        key = self._derive_key(master_password, salt)
        fernet = Fernet(key)
        token = fernet.encrypt(b"verified")
        self.VERIFY_PATH.write_bytes(token)

    def _verify_master_password(self, master_password: str) -> bool:
        if not all(p.exists() for p in [self.SALT_PATH, self.VERIFY_PATH]):
            return False

        salt = self.SALT_PATH.read_bytes()
        stored_token = self.VERIFY_PATH.read_bytes()

        try:
            key = self._derive_key(master_password, salt)
            fernet = Fernet(key)
            fernet.decrypt(stored_token)
            self._fernet = fernet
            return True
        except Exception:
            return False

    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def unlock(self, master_password: str) -> bool:
        return self._verify_master_password(master_password)

    def unlock_with_default(self) -> bool:
        return self._try_auto_unlock()

    def can_store_password(self) -> bool:
        return self._fernet is not None

    def set_password(self, host_name: str, password: str) -> None:
        if not self._fernet:
            raise ValueError("Vault is locked. Unlock it first.")

        passwords = self._read_vault()
        encrypted = self._fernet.encrypt(password.encode()).decode()
        passwords[host_name] = encrypted
        self._write_vault(passwords)

    def get_password(self, host_name: str) -> Optional[str]:
        if not self._fernet:
            raise ValueError("Vault is locked. Unlock it first.")

        passwords = self._read_vault()
        encrypted = passwords.get(host_name)
        if encrypted:
            return self._fernet.decrypt(encrypted.encode()).decode()
        return None

    def remove_password(self, host_name: str) -> None:
        if not self._fernet:
            raise ValueError("Vault is locked. Unlock it first.")

        passwords = self._read_vault()
        passwords.pop(host_name, None)
        self._write_vault(passwords)

    def has_password(self, host_name: str) -> bool:
        if not self.VAULT_PATH.exists():
            return False
        passwords = self._read_vault()
        return host_name in passwords

    def _read_vault(self) -> dict[str, str]:
        if not self.VAULT_PATH.exists():
            return {}
        try:
            return json.loads(self.VAULT_PATH.read_text())
        except json.JSONDecodeError:
            return {}

    def _write_vault(self, passwords: dict[str, str]) -> None:
        self.VAULT_PATH.write_text(json.dumps(passwords))

    @staticmethod
    def vault_exists() -> bool:
        return PasswordVault.VAULT_PATH.exists()
