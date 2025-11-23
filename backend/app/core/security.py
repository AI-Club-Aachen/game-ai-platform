"""Security module with password validation, token handling, and secure comparisons"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


logger = logging.getLogger(__name__)

# Configure bcrypt with appropriate cost factor (12 is secure and reasonable)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Higher rounds = slower but more secure
)


def hash_password(password: str) -> str:
    """
    Hash password with bcrypt using configured cost factor.

    Args:
        password: Plain text password to hash

    Returns:
        str: Hashed password

    Raises:
        ValueError: If password is too weak or invalid
    """
    validate_password_strength(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against bcrypt hash using constant-time comparison.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # pwd_context.verify already uses constant-time comparison internally
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError) as e:
        logger.warning(f"Password verification error: {type(e).__name__}")
        return False


def validate_password_strength(password: str) -> None:
    """
    Validate password strength requirements.

    Args:
        password: Password to validate

    Raises:
        ValueError: If password doesn't meet requirements
    """
    # Length check
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")

    # Character diversity checks
    has_uppercase = any(c.isupper() for c in password)
    has_lowercase = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/\\`~" for c in password)

    if not has_uppercase:
        raise ValueError("Password must contain at least one uppercase letter (A-Z)")

    if not has_lowercase:
        raise ValueError("Password must contain at least one lowercase letter (a-z)")

    if not has_digit:
        raise ValueError("Password must contain at least one digit (0-9)")

    if not has_special:
        raise ValueError("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:',.<>?/\\`~)")

    # Check for common weak patterns
    weak_patterns = ["password", "123456", "qwerty", "admin", "user"]
    if any(pattern in password.lower() for pattern in weak_patterns):
        raise ValueError("Password contains weak patterns, please use a stronger password")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token with expiration.

    Args:
        data: Dictionary of claims to encode (e.g., {"sub": user_id, "role": "admin"})
        expires_delta: Custom expiration time. If None, uses JWT_ACCESS_TOKEN_EXPIRE_HOURS from settings

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)

    # Add standard claims
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),  # Issued at time
            "nbf": datetime.now(UTC),  # Not before time
        }
    )

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token encoding error: {e}")
        raise


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate JWT token with proper error handling.

    Args:
        token: JWT token to decode

    Returns:
        Optional[dict]: Decoded token payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_exp": True,  # Verify expiration time
                "verify_signature": True,  # Verify signature
            },
        )
        return payload
    except JWTError as e:
        logger.debug(f"Token decode error: {type(e).__name__}")
        return None
    except Exception as e:
        logger.error(f"Unexpected token decode error: {e}")
        return None


def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.

    This function uses HMAC to prevent attackers from determining
    the correct value by measuring response times.

    Args:
        a: First string to compare
        b: Second string to compare

    Returns:
        bool: True if strings are equal, False otherwise
    """
    try:
        return hmac.compare_digest(a, b)
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        return False


def generate_secure_random_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Uses secrets module which is suitable for security-sensitive operations.

    Args:
        length: Desired length of token (in bytes). URL-safe base64 encoding
                will make it approximately 4/3 this length

    Returns:
        str: URL-safe base64 encoded random token
    """
    import secrets

    if length < 16:
        raise ValueError("Token length must be at least 16 bytes for security")

    if length > 256:
        raise ValueError("Token length must not exceed 256 bytes")

    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """
    Hash token using SHA-256 for secure storage.

    Tokens should be hashed before storage in database to prevent
    leakage of valid tokens if database is compromised.

    Args:
        token: Token to hash

    Returns:
        str: Hexadecimal SHA-256 hash of token
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_against_hash(token: str, token_hash: str) -> bool:
    """
    Verify token against hash using constant-time comparison.

    Args:
        token: Plain text token to verify
        token_hash: Hashed token from database

    Returns:
        bool: True if token matches hash, False otherwise
    """
    try:
        computed_hash = hash_token(token)
        # Use secure_compare to prevent timing attacks
        return secure_compare(computed_hash, token_hash)
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return False


def is_token_expired(expires_at: datetime | None) -> bool:
    """
    Check if token has expired.

    Args:
        expires_at: Expiration datetime in UTC. If None, considered expired

    Returns:
        bool: True if expired or None, False if still valid
    """
    if expires_at is None:
        return True

    try:
        now = datetime.now(UTC)
        # Add small buffer (1 second) to account for clock skew
        return now >= (expires_at - timedelta(seconds=1))
    except Exception as e:
        logger.error(f"Expiry check error: {e}")
        return True  # Fail secure - treat as expired


def get_token_expiry_time(hours: int = 24) -> datetime:
    """
    Calculate token expiry datetime.

    Args:
        hours: Number of hours until expiry

    Returns:
        datetime: Expiry datetime in UTC
    """
    return datetime.now(UTC) + timedelta(hours=hours)
