"""Token generation and verification with security best practices"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

# Token length in bytes (32 bytes = 256 bits of entropy)
TOKEN_LENGTH = 32


def generate_secure_token() -> str:
    """
    Generate a cryptographically secure random token.

    Returns:
        str: Hex-encoded token (64 characters)
    """
    return secrets.token_hex(TOKEN_LENGTH)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.
    Only the hash is stored in database, not the token itself.

    Args:
        token: Plain text token

    Returns:
        str: SHA-256 hash of token (hex-encoded)
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    """
    Verify a provided token against its stored hash.

    Args:
        token: Plain text token to verify
        stored_hash: Stored SHA-256 hash

    Returns:
        bool: True if token matches hash, False otherwise
    """
    token_hash = hash_token(token)
    return secrets.compare_digest(token_hash, stored_hash)


def get_token_expiry(hours: int = 0, minutes: int = 0) -> datetime:
    """
    Calculate token expiry time with UTC timezone.

    Args:
        hours: Hours until expiry
        minutes: Minutes until expiry

    Returns:
        datetime: UTC expiry timestamp
    """
    return datetime.now(timezone.utc) + timedelta(hours=hours, minutes=minutes)


def is_token_expired(expires_at: Optional[datetime]) -> bool:
    """
    Check if token has expired.

    Args:
        expires_at: Token expiry timestamp

    Returns:
        bool: True if expired, False if still valid
    """
    if expires_at is None:
        return True
    return datetime.now(timezone.utc) > expires_at
