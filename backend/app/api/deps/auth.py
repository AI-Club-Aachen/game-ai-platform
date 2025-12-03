"""Authentication dependencies for JWT validation and user extraction"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps.services import get_user_repository
from app.api.repositories.user import UserRepository
from app.core.security import decode_access_token
from app.models.user import User


logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: Bearer token from request header
        user_repository: User repository bound to current DB session

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token with validation
    payload = decode_access_token(token)

    if payload is None:
        logger.warning("Invalid token attempted from client")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        logger.warning("Token missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse UUID
    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError) as e:
        logger.warning("Invalid UUID in token: %s", user_id_str)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Fetch user via repository
    user = user_repository.get_by_id(user_id)

    if user is None:
        logger.warning("User not found for ID: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_current_user(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User | None:
    """
    Optional dependency for endpoints that support both authenticated and anonymous access.
    Returns None if no valid token is provided, otherwise returns the user.

    Args:
        user_repository: User repository bound to current DB session
        credentials: Optional Bearer token from request header

    Returns:
        Optional[User]: The user if authenticated, None if not
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        logger.debug("Invalid optional token")
        return None

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        logger.debug("Optional token missing 'sub' claim")
        return None

    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError):
        logger.debug("Invalid UUID in optional token")
        return None

    user = user_repository.get_by_id(user_id)

    if user is None:
        logger.debug("User not found for optional auth: %s", user_id)
        return None

    return user


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_current_user)]
