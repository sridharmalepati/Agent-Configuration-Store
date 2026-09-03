import pytest
from cryptography.fernet import Fernet

from repo_service.config import get_settings
from repo_service.security import decrypt_token, encrypt_token


def test_encrypt_decrypt_with_unpadded_fernet_key(monkeypatch) -> None:
    generated_key = Fernet.generate_key().decode("utf-8")
    unpadded_key = generated_key.rstrip("=")

    monkeypatch.setenv("ACCESS_TOKEN_ENCRYPTION_KEY", unpadded_key)
    get_settings.cache_clear()

    try:
        encrypted = encrypt_token("secret-token")
        decrypted = decrypt_token(encrypted)
        assert decrypted == "secret-token"
    finally:
        get_settings.cache_clear()



def test_encrypt_token_rejects_invalid_fernet_key(monkeypatch) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_ENCRYPTION_KEY", "not-a-valid-key")
    get_settings.cache_clear()

    try:
        with pytest.raises(ValueError, match="ACCESS_TOKEN_ENCRYPTION_KEY"):
            encrypt_token("secret-token")
    finally:
        get_settings.cache_clear()
