"""Service and repository factory dependencies"""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.api.repositories.user import UserRepository
from app.api.services.auth import AuthService
from app.api.services.email import EmailNotificationService
from app.api.services.user import UserService
from app.core.email import EmailClient, email_client
from app.db.session import get_session


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


def get_email_client() -> EmailClient:
    """Provide the shared EmailClient instance."""
    return email_client


def get_email_notification_service(
    client: Annotated[EmailClient, Depends(get_email_client)],
) -> EmailNotificationService:
    """Provide an EmailNotificationService with an injected EmailClient."""
    return EmailNotificationService(client)


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    email_notifications: Annotated[
        EmailNotificationService,
        Depends(get_email_notification_service),
    ],
) -> AuthService:
    """Provide an AuthService with injected UserRepository and EmailNotificationService."""
    return AuthService(user_repository, email_notifications)
