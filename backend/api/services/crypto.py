from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


ENCRYPTED_VALUE_PREFIX = "fernet:"


def _token_fernets() -> list[Fernet]:
    keys = [
        settings.GOOGLE_TOKEN_ENCRYPTION_KEY,
        *settings.GOOGLE_TOKEN_ENCRYPTION_FALLBACK_KEYS,
    ]
    keys = [key for key in keys if key]
    if not keys:
        if settings.DEBUG:
            return []
        raise ImproperlyConfigured("GOOGLE_TOKEN_ENCRYPTION_KEY must be configured when DEBUG=false.")

    fernets: list[Fernet] = []
    for key in keys:
        try:
            fernets.append(Fernet(key.encode("ascii")))
        except Exception as exc:
            raise ImproperlyConfigured("GOOGLE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key.") from exc
    return fernets


def is_encrypted_value(value: str) -> bool:
    return value.startswith(ENCRYPTED_VALUE_PREFIX)


def encrypt_text(value: str) -> str:
    if not value or is_encrypted_value(value):
        return value

    fernets = _token_fernets()
    if not fernets:
        return value

    token = fernets[0].encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_VALUE_PREFIX}{token}"


def decrypt_text(value: str) -> str:
    if not value or not is_encrypted_value(value):
        return value

    token = value.removeprefix(ENCRYPTED_VALUE_PREFIX).encode("ascii")
    for fernet in _token_fernets():
        try:
            return fernet.decrypt(token).decode("utf-8")
        except InvalidToken:
            continue

    raise ImproperlyConfigured("Unable to decrypt a stored Google OAuth token with configured keys.")
