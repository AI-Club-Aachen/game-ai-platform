"""Application-level email notification service (verification, password reset)."""

import logging
from typing import Optional

from app.core.config import settings
from app.core.email import EmailClient

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """
    High-level email notification service.

    Responsibilities:
    - Build subjects and bodies for domain-specific emails
      (verification, password reset)
    - Call EmailClient to actually send the message
    """

    def __init__(self, email_client: EmailClient) -> None:
        self._client = email_client

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        token: str,
    ) -> bool:
        """
        Send email verification link.

        Args:
            to_email: Recipient email address
            username: User's display name
            token: Verification token (plain, not hashed)
        """
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Welcome, {self._escape_html(username)}!</h2>

                    <p>Thank you for signing up. Please verify your email address to complete your registration.</p>

                    <div style="margin: 30px 0;">
                        <a href="{verify_url}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Verify Email
                        </a>
                    </div>

                    <p style="color: #7f8c8d; font-size: 14px;">
                        Or copy this link:<br>
                        <code style="background-color: #f5f5f5; padding: 5px 10px; border-radius: 3px;">{verify_url}</code>
                    </p>

                    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">

                    <p style="color: #7f8c8d; font-size: 12px;">
                        This verification link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.
                    </p>

                    <p style="color: #7f8c8d; font-size: 12px;">
                        If you didn't create this account, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """

        text_content = f"""
Welcome, {username}!

Thank you for signing up. Please verify your email address to complete your registration.

Verify Email:
{verify_url}

Or copy this link:
{verify_url}

This verification link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.

If you didn't create this account, please ignore this email.
        """.strip()

        return await self._client.send_email(
            to_email=to_email,
            subject="Verify Your Email Address",
            html_content=html_content,
            text_content=text_content,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        token: str,
    ) -> bool:
        """
        Send password reset link via email.

        Args:
            to_email: Recipient email address
            username: User's display name
            token: Password reset token (plain, not hashed)
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Password Reset Request</h2>

                    <p>Hi {self._escape_html(username)},</p>

                    <p>We received a request to reset your password. Click the link below to create a new password:</p>

                    <div style="margin: 30px 0;">
                        <a href="{reset_url}" style="display: inline-block; background-color: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Reset Password
                        </a>
                    </div>

                    <p style="color: #7f8c8d; font-size: 14px;">
                        Or copy this link:<br>
                        <code style="background-color: #f5f5f5; padding: 5px 10px; border-radius: 3px;">{reset_url}</code>
                    </p>

                    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">

                    <p style="color: #7f8c8d; font-size: 12px;">
                        This reset link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
                    </p>

                    <p style="color: #7f8c8d; font-size: 12px;">
                        If you didn't request this, please secure your account and ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """

        text_content = f"""
Password Reset Request

Hi {username},

We received a request to reset your password. Click the link below to create a new password:

Reset Password:
{reset_url}

Or copy this link:
{reset_url}

This reset link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.

If you didn't request this, please secure your account and ignore this email.
        """.strip()

        return await self._client.send_email(
            to_email=to_email,
            subject="Password Reset Request",
            html_content=html_content,
            text_content=text_content,
        )

    @staticmethod
    def _escape_html(text: Optional[str]) -> str:
        """
        Escape HTML special characters to prevent XSS in emails.

        Args:
            text: Text to escape

        Returns:
            str: Escaped text safe for HTML
        """
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)

        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
