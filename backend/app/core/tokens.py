"""Token generation and verification with secure comparisons and validation"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.security import secure_compare


logger = logging.getLogger(__name__)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token using secrets module.

    Args:
        length: Desired token length in bytes. URL-safe base64 encoding
                will make it approximately 4/3 this length

    Returns:
        str: URL-safe base64 encoded random token

    Raises:
        ValueError: If length is outside valid range (16-256 bytes)

    Example:
        >>> token = generate_secure_token(32)
        >>> len(token)  # Will be ~43 characters
    """
    if length < 16:
        raise ValueError("Token length must be at least 16 bytes for security")

    if length > 256:
        raise ValueError("Token length must not exceed 256 bytes")

    try:
        return secrets.token_urlsafe(length)
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        raise


def hash_token(token: str) -> str:
    """
    Hash token using SHA-256 for secure storage.

    Tokens should be hashed before storage in database to prevent
    leakage of valid tokens if database is compromised.

    Args:
        token: Plain text token to hash

    Returns:
        str: Hexadecimal SHA-256 hash of token

    Example:
        >>> token = "abc123"
        >>> hash_val = hash_token(token)
        >>> len(hash_val)  # 64 characters (256 bits in hex)
    """
    try:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.error(f"Token hashing error: {e}")
        raise


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify token against hash using constant-time comparison.

    This uses HMAC constant-time comparison to prevent timing attacks
    where attackers could determine if a token is valid by measuring
    response times.

    Args:
        token: Plain text token to verify
        token_hash: Hashed token from database

    Returns:
        bool: True if token matches hash, False otherwise

    Example:
        >>> token = "mytoken123"
        >>> token_hash = hash_token(token)
        >>> verify_token_hash(token, token_hash)
        True
        >>> verify_token_hash("wrongtoken", token_hash)
        False
    """
    try:
        computed_hash = hash_token(token)
        # Use secure_compare to prevent timing attacks
        return secure_compare(computed_hash, token_hash)
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return False  # Fail secure


def get_token_expiry_time(hours: int) -> datetime:
    """
    Calculate token expiry datetime in UTC.

    Args:
        hours: Number of hours until expiry

    Returns:
        datetime: Expiry datetime in UTC

    Raises:
        ValueError: If hours is invalid (< 0 or > 10 years)

    Example:
        >>> expiry = get_token_expiry_time(24)
        >>> expiry > datetime.now(timezone.utc)
        True
    """
    if hours <= 0:
        raise ValueError("Hours must be greater than 0")

    if hours > 87660:  # ~10 years
        raise ValueError("Hours value is unreasonably large")

    try:
        return datetime.now(UTC) + timedelta(hours=hours)
    except Exception as e:
        logger.error(f"Expiry time calculation error: {e}")
        raise


def is_token_expired(expires_at: datetime | None) -> bool:
    """
    Check if token has expired, accounting for clock skew.

    Args:
        expires_at: Expiration datetime in UTC. If None, considered expired

    Returns:
        bool: True if expired or None, False if still valid

    Example:
        >>> future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        >>> is_token_expired(future_time)
        False

        >>> past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        >>> is_token_expired(past_time)
        True
    """
    if expires_at is None:
        return True

    try:
        now = datetime.now(UTC)

        # Ensure expires_at is timezone-aware
        if expires_at.tzinfo is None:
            logger.debug(f"Converting naive datetime to UTC-aware: {expires_at}")
            expires_at = expires_at.replace(tzinfo=UTC)

        # Add 1-second buffer to account for clock skew between services
        buffer = timedelta(seconds=1)
        is_expired = now > (expires_at + buffer)

        return is_expired

    except TypeError as e:
        # This handles "can't compare offset-naive and offset-aware" errors
        logger.error(
            f"Timezone comparison error in token expiry check: {e} | "
            f"expires_at={expires_at}, tzinfo={getattr(expires_at, 'tzinfo', 'N/A')}"
        )
        return True  # Fail secure - treat as expired
    except Exception as e:
        logger.error(f"Unexpected error in token expiry check: {e}")
        return True  # Fail secure - treat as expired


def create_email_verification_token() -> tuple[str, str, datetime]:
    """
    Generate email verification token with hash and expiry.

    Returns:
        tuple: (plain_token, token_hash, expiry_datetime)

    Example:
        >>> token, token_hash, expiry = create_email_verification_token()
        >>> verify_token_hash(token, token_hash)
        True
    """
    plain_token = generate_secure_token(32)
    token_hash = hash_token(plain_token)
    expiry = get_token_expiry_time(settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)

    return plain_token, token_hash, expiry


def create_password_reset_token() -> tuple[str, str, datetime]:
    """
    Generate password reset token with hash and expiry.

    Returns:
        tuple: (plain_token, token_hash, expiry_datetime)

    Example:
        >>> token, token_hash, expiry = create_password_reset_token()
        >>> verify_token_hash(token, token_hash)
        True
    """
    plain_token = generate_secure_token(32)
    token_hash = hash_token(plain_token)
    expiry = get_token_expiry_time(settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES / 60)

    return plain_token, token_hash, expiry


def validate_token_format(token: str, min_length: int = 16) -> bool:
    """
    Validate token format before verification.

    Args:
        token: Token to validate
        min_length: Minimum token length

    Returns:
        bool: True if format is valid

    Example:
        >>> validate_token_format("valid_token_here_")
        True
        >>> validate_token_format("")
        False
    """
    if not isinstance(token, str):
        logger.warning(f"Token is not a string: {type(token)}")
        return False

    if len(token) < min_length:
        logger.warning(f"Token too short: {len(token)} < {min_length}")
        return False

    if len(token) > 512:  # Reasonable max for base64 tokens
        logger.warning(f"Token too long: {len(token)} > 512")
        return False

    return True


def safe_verify_token_hash(token: str, token_hash: str | None) -> bool:
    """
    Safely verify token against hash with format validation.

    This is a wrapper around verify_token_hash that adds input validation
    and logging, suitable for direct use in API endpoints.

    Args:
        token: Plain text token to verify
        token_hash: Hashed token from database (can be None)

    Returns:
        bool: True if token matches, False otherwise

    Example:
        >>> token = generate_secure_token()
        >>> token_hash = hash_token(token)
        >>> safe_verify_token_hash(token, token_hash)
        True
    """
    # Validate inputs
    if not validate_token_format(token):
        return False

    if not isinstance(token_hash, str) or not token_hash:
        logger.debug("Token hash is None or invalid")
        return False

    if len(token_hash) != 64:  # SHA-256 in hex is 64 chars
        logger.warning(f"Invalid token hash length: {len(token_hash)}")
        return False

    # Perform verification
    return verify_token_hash(token, token_hash)


def cleanup_expired_tokens_info(expires_at: datetime | None) -> dict:
    """
    Get information about token cleanup for logging.

    Args:
        expires_at: Token expiration datetime

    Returns:
        dict: Information about the token expiry status

    Example:
        >>> info = cleanup_expired_tokens_info(datetime.now(timezone.utc))
        >>> info["is_expired"]
        True
    """
    if expires_at is None:
        return {"is_expired": True, "reason": "No expiry set"}

    is_expired = is_token_expired(expires_at)

    return {
        "is_expired": is_expired,
        "expires_at": expires_at.isoformat(),
        "time_until_expiry": (expires_at - datetime.now(UTC)).total_seconds(),
    }
