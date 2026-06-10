"""Authorization and permission dependencies"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps.auth import (
    get_current_user,
    security,
    verify_worker_api_key,
    worker_api_key_header,
)
from app.api.deps.services import get_user_repository
from app.api.repositories.user import UserRepository
from app.models.user import User, UserRole


logger = logging.getLogger(__name__)


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


def verify_user_role(required_role: UserRole) -> Callable:
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


def get_verified_user_or_higher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency for mutating endpoints: requires an email-verified account with
    at least the USER role. Verified guests are read-only and get 403 here.
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
    return verify_user_role(UserRole.USER)(current_user)


@dataclass
class RequestActor:
    """Caller of a worker-readable endpoint: either the worker (via x-api-key) or a JWT user."""

    is_worker: bool
    user: User | None


def get_worker_or_verified_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    api_key: str | None = Security(worker_api_key_header),
) -> RequestActor:
    """
    Combined dependency for the few read endpoints the build/match workers need
    (submission read/download, agent read, match read). A valid worker API key
    grants read access WITHOUT a synthetic user identity; otherwise normal JWT
    auth applies and the caller must be email-verified. Ownership checks for
    JWT users remain the route's responsibility.
    """
    if verify_worker_api_key(api_key):
        return RequestActor(is_worker=True, user=None)

    user = get_current_user(credentials, user_repository)
    return RequestActor(is_worker=False, user=verify_email_verified(user))


# Type aliases for common dependencies
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
VerifiedUser = Annotated[User, Depends(verify_email_verified)]
AdminOnly = CurrentAdmin
VerifiedGuestOrHigher = Annotated[User, Depends(verify_email_verified)]
VerifiedUserOrHigher = Annotated[User, Depends(get_verified_user_or_higher)]
WorkerOrVerifiedUser = Annotated[RequestActor, Depends(get_worker_or_verified_user)]
