import hashlib
import os
import secrets
from typing import Tuple

ITERATIONS = 100_000
HASH_ALGO = 'sha256'

def hash_password(password: str, salt: bytes = None) -> Tuple[str, str]:
    """
    Hashes a password with PBKDF2-HMAC-SHA256 and a cryptographically secure salt.
    Returns (hex_hash, hex_salt).
    """
    if salt is None:
        salt = os.urandom(16)
    pw_bytes = password.encode('utf-8')
    key = hashlib.pbkdf2_hmac(HASH_ALGO, pw_bytes, salt, ITERATIONS)
    return key.hex(), salt.hex()

def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verifies a plain-text password against a stored hash and salt.
    """
    try:
        salt = bytes.fromhex(stored_salt)
        computed_hash, _ = hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False

def generate_session_token() -> str:
    """Generates a high-entropy URL-safe session token."""
    return secrets.token_urlsafe(32)
