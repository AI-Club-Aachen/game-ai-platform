"""API dependencies for authentication and database access"""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User, UserRole

from app.api.repositories.user import UserRepository
from app.api.services.user import UserService
from app.api.services.auth import AuthService

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_user_repository(
    session: Annotated[Session, Depends(get_session)],
) -> UserRepository:
    """Provide a UserRepository bound to the current DB session."""
    return UserRepository(session)


def get_user_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    """Provide a UserService with an injected UserRepository."""
    return UserService(user_repository)


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    """Provide an AuthService with an injected UserRepository."""
    return AuthService(user_repository)


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
    user_id_str: Optional[str] = payload.get("sub")
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
    except (ValueError, TypeError):
        logger.warning("Invalid UUID in token: %s", user_id_str)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

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


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to ensure current user has admin role.

    Args:
        current_user: The authenticated user

    Returns:
        User: The admin user

    Raises:
        HTTPException: 403 if user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning("Non-admin user %s attempted admin action", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required.",
        )
    return current_user


def get_optional_current_user(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> Optional[User]:
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

    user_id_str: Optional[str] = payload.get("sub")
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


def verify_email_verified(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to ensure user has verified their email.

    Args:
        current_user: The authenticated user

    Returns:
        User: The user with verified email

    Raises:
        HTTPException: 403 if email is not verified
    """
    if not current_user.email_verified:
        logger.warning(
            "Unverified user %s attempted action requiring verification",
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required to access this resource.",
        )
    return current_user


def verify_user_role(required_role: UserRole):
    """
    Factory function to create a dependency that verifies user has a specific role.

    Args:
        required_role: The minimum required role

    Returns:
        Callable: Dependency function
    """

    def check_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has required role."""
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.USER: 1,
            UserRole.ADMIN: 2,
        }

        if role_hierarchy.get(current_user.role, -1) < role_hierarchy.get(
            required_role,
            -1,
        ):
            logger.warning(
                "User %s with role %s attempted %s action",
                current_user.id,
                current_user.role,
                required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {required_role.value} role or higher.",
            )
        return current_user

    return check_role


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
VerifiedUser = Annotated[User, Depends(verify_email_verified)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_current_user)]
