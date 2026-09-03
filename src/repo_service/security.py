"""Encryption utilities for access tokens."""
import base64
import binascii

from cryptography.fernet import Fernet

from .config import get_settings


def _normalized_fernet_key(raw_key: str) -> bytes:
    key = raw_key.strip()
    if not key:
        raise ValueError("ACCESS_TOKEN_ENCRYPTION_KEY is required")

    # Normalize any trailing '=' first, then re-apply required padding.
    key_without_padding = key.rstrip("=")
    key_with_padding = key_without_padding + ("=" * (-len(key_without_padding) % 4))
    try:
        decoded = base64.urlsafe_b64decode(key_with_padding.encode("utf-8"))
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "ACCESS_TOKEN_ENCRYPTION_KEY must be valid URL-safe base64"
        ) from exc

    if len(decoded) != 32:
        raise ValueError(
            "ACCESS_TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes"
        )

    return base64.urlsafe_b64encode(decoded)


def _build_cipher() -> Fernet:
    return Fernet(_normalized_fernet_key(get_settings().access_token_encryption_key))


def encrypt_token(raw_token: str) -> str:
    return _build_cipher().encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    return _build_cipher().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


def mask_token(raw_token: str) -> str:
    if len(raw_token) <= 4:
        return "*" * len(raw_token)
    return "*" * (len(raw_token) - 4) + raw_token[-4:]
