"""Authorization and permission dependencies"""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.api.deps.auth import get_current_user
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


# Type aliases for common dependencies
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
VerifiedUser = Annotated[User, Depends(verify_email_verified)]
