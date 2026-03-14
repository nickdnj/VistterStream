"""Symmetric encryption for secrets at rest (camera passwords, API keys, tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
Requires ENCRYPTION_KEY environment variable to be set.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

_key = os.getenv("ENCRYPTION_KEY")
if not _key:
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable must be set. "
        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

_fernet = Fernet(_key.encode() if isinstance(_key, str) else _key)


def encrypt(value: str) -> str:
    """Encrypt a string value. Returns a Fernet token (base64-encoded)."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted value back to plaintext."""
    try:
        return _fernet.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise ValueError("Unable to decrypt value: not a valid Fernet token")
