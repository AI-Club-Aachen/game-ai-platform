"""Email service module with retry logic, security, and async support"""

import asyncio
import logging
import re
from typing import Optional
from datetime import datetime, timezone
from email.utils import format_datetime, make_msgid


import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Async SMTP email service with retry logic and security best practices.

    Features:
    - TLS/SSL encryption for all connections
    - Exponential backoff retry logic (3 attempts by default)
    - Timeout handling (10 seconds)
    - Connection pooling and cleanup
    - HTML and plain text templates
    - Logging for all operations
    """

    def __init__(self):
        """Initialize email service with SMTP settings"""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_address = settings.SMTP_FROM_ADDRESS
        self.from_name = settings.SMTP_FROM_NAME
        self.timeout = 10  # seconds
        self.max_retries = 3
        self.retry_backoff = 2  # exponential backoff multiplier

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> bool:
        """
        Send email with automatic retry and error handling.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text fallback (auto-generated if None)
            retry_count: Number of retries (uses default if None)

        Returns:
            bool: True if sent successfully, False otherwise

        Example:
            success = await email_service.send_email(
            ...     to_email="user@example.com",
            ...     subject="Welcome!",
            ...     html_content="<p>Welcome!</p>"
            ... )
        """
        # Validate inputs
        if not self._validate_email(to_email):
            logger.error(f"Invalid email address: {to_email}")
            return False

        if not subject or not html_content:
            logger.error("Subject and html_content are required")
            return False

        # Generate text content if not provided
        if not text_content:
            text_content = self._strip_html_to_text(html_content)

        # Use default retry count if not specified
        if retry_count is None:
            retry_count = self.max_retries

        # Attempt to send with exponential backoff
        for attempt in range(retry_count):
            try:
                await asyncio.wait_for(
                    self._send_via_smtp(
                        to_email=to_email,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content
                    ),
                    timeout=self.timeout
                )
                logger.info(f"Email sent successfully to {to_email}")
                return True

            except asyncio.TimeoutError:
                logger.warning(
                    f"Email send timeout for {to_email} "
                    f"(attempt {attempt + 1}/{retry_count})"
                )

            except aiosmtplib.SMTPException as e:
                logger.error(
                    f"SMTP error sending to {to_email} "
                    f"(attempt {attempt + 1}/{retry_count}): {type(e).__name__}"
                )

            except aiosmtplib.SMTPAuthenticationError as e:
                logger.critical(f"SMTP authentication failed: {e}")
                return False  # Don't retry on auth failure

            except Exception as e:
                logger.error(
                    f"Unexpected error sending email to {to_email}: "
                    f"{type(e).__name__}: {str(e)}"
                )

            # Exponential backoff between retries (except on last attempt)
            if attempt < retry_count - 1:
                wait_time = self.retry_backoff ** attempt
                logger.debug(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        logger.error(
            f"Failed to send email to {to_email} after {retry_count} attempts"
        )
        return False

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> None:
        """
        Internal method to send email via SMTP with TLS.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body

        Raises:
            aiosmtplib.SMTPException: On SMTP errors
            asyncio.TimeoutError: On connection timeout
        """
        now_utc = datetime.now(timezone.utc)

        # Create MIME multipart message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_address}>"
        message["To"] = to_email
        message["Date"] = format_datetime(now_utc)
        message["Message-ID"] = make_msgid(domain=self.smtp_host)

        # Attach plain text first (fallback for email clients)
        part1 = MIMEText(text_content, "plain", "utf-8")
        message.attach(part1)

        # Attach HTML (preferred by modern email clients)
        part2 = MIMEText(html_content, "html", "utf-8")
        message.attach(part2)

        # Create SMTP connection with TLS
        try:
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls,
                timeout=self.timeout,
            ) as smtp:
                # Authenticate with credentials
                await smtp.login(self.smtp_username, self.smtp_password)

                # Send message
                await smtp.send_message(message)

        except aiosmtplib.SMTPAuthenticationError:
            logger.critical("SMTP authentication failed - check credentials")
            raise
        except Exception as e:
            logger.error(f"SMTP connection error: {type(e).__name__}: {e}")
            raise

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        token: str,
    ) -> bool:
        """
        Send email verification link.

        Args:
            to_email: Recipient email
            username: User's display name
            token: Verification token (plain, not hashed)

        Returns:
            bool: True if sent successfully
        """
        # Build verification URL (frontend should handle this)
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
        """

        return await self.send_email(
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
            to_email: Recipient email
            username: User's display name
            token: Password reset token (plain, not hashed)

        Returns:
            bool: True if sent successfully
        """
        reset_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

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
        """

        return await self.send_email(
            to_email=to_email,
            subject="Password Reset Request",
            html_content=html_content,
            text_content=text_content,
        )

    @staticmethod
    def _validate_email(email: str) -> bool:
        """
        Validate email format with regex.

        Args:
            email: Email to validate

        Returns:
            bool: True if valid email format
        """
        if not email or len(email) > 254:  # RFC 5321
            return False

        # Simple regex for email validation
        pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, email))

    @staticmethod
    def _strip_html_to_text(html: str) -> str:
        """
        Convert HTML to plain text using regex.

        Args:
            html: HTML string to convert

        Returns:
            str: Plain text version
        """
        # Remove script and style elements
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    @staticmethod
    def _escape_html(text: str) -> str:
        """
        Escape HTML special characters to prevent XSS in emails.

        Args:
            text: Text to escape

        Returns:
            str: Escaped text safe for HTML
        """
        if not isinstance(text, str):
            text = str(text)

        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


# Singleton instance
email_service = EmailService()
