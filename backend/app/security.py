from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Final

_ITERATIONS: Final[int] = 100_000
_SALT_BYTES: Final[int] = 16


def hash_password(password: str) -> str:
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split('$', 1)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), _ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected)
