"""Credential encryption/decryption using Fernet symmetric encryption."""
import hashlib
import base64
import json
from cryptography.fernet import Fernet
from backend.config import settings


def _get_fernet() -> Fernet:
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_credentials(data: dict) -> str:
    return _get_fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(encrypted: str) -> dict:
    try:
        return json.loads(_get_fernet().decrypt(encrypted.encode()).decode())
    except Exception:
        return {}
