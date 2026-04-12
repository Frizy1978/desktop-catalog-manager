from __future__ import annotations

import hashlib
import secrets


PBKDF2_ITERATIONS = 210_000


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    _, computed_hash_hex = hash_password(password=password, salt_hex=salt_hex)
    return secrets.compare_digest(computed_hash_hex, expected_hash_hex)
