"""
API dependencies for authentication and database access.

This package provides dependency injection for FastAPI routes, organized by concern:
- services: Service and repository factory functions
- auth: Authentication (JWT validation, user extraction)
- permissions: Authorization (role checks, email verification)
"""

# Re-export all dependencies for backward compatibility
# This allows existing imports like `from app.api.deps import CurrentUser` to continue working

# Service factories
# Authentication
from app.api.deps.auth import (
    CurrentUser,
    OptionalUser,
    get_current_user,
    get_optional_current_user,
)

# Authorization/Permissions
from app.api.deps.permissions import (
    CurrentAdmin,
    VerifiedUser,
    get_current_admin,
    verify_email_verified,
    verify_user_role,
)
from app.api.deps.services import (
    get_auth_service,
    get_email_client,
    get_email_notification_service,
    get_match_service,
    get_submission_service,
    get_user_repository,
    get_user_service,
)


__all__ = [
    # Service factories
    "get_auth_service",
    "get_email_client",
    "get_email_notification_service",
    "get_user_repository",
    "get_user_service",
    "get_submission_service",
    "get_match_service",
    # Authentication
    "CurrentUser",
    "OptionalUser",
    "get_current_user",
    "get_optional_current_user",
    # Authorization/Permissions
    "CurrentAdmin",
    "VerifiedUser",
    "get_current_admin",
    "verify_email_verified",
    "verify_user_role",
]
