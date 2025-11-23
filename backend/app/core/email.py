"""Email client with SMTP transport, retry logic, and environment-aware behavior."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import format_datetime, make_msgid
from typing import Optional

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailClient:
    """
    Low-level SMTP email client with retry logic and environment-aware behavior.

    Responsibilities:
    - Read SMTP configuration from settings
    - Decide whether to actually send or only log (dev vs staging/prod)
    - Build and send MIME messages
    - Handle timeouts, retries, and logging of errors
    """

    def __init__(self) -> None:
        """Initialize email client with SMTP settings."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS

        # Fallback from address in dev if none is provided
        self.from_address = settings.SMTP_FROM_ADDRESS or "dev-noreply@example.local"
        self.from_name = settings.SMTP_FROM_NAME

        self.timeout = 10  # seconds
        self.max_retries = 3
        self.retry_backoff = 2  # exponential backoff multiplier

        # Flags derived from settings / ENVIRONMENT
        self.smtp_configured = settings.smtp_configured
        self.smtp_required = settings.smtp_required
        self.is_development = settings.is_development

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
        """
        # --- local development (SMTP not configured) ---
        if self.is_development or not self.smtp_configured:
            # Dev behavior: log instead of sending
            logger.warning(
                "SMTP not configured in development; email will NOT be sent, only logged."
            )
            logger.info("Dev email to=%s subject=%s", to_email, subject)
            logger.info("Dev email HTML content:\n%s", html_content)
            return True  # Pretend success so flows continue

        if self.smtp_required:
            # In staging/production this should not happen because Settings
            # already enforces SMTP, but fail safe if it does.
            logger.critical(
                "SMTP is required in this environment but not configured; cannot send email."
            )
            return False

        # Non-required, non-dev fallback (just in case)
        logger.error("SMTP not configured; skipping email send.")
        return False

        # --- staging / prod (SMTP configured) ---

        # Validate inputs
        if not self._validate_email(to_email):
            logger.error("Invalid email address: %s", to_email)
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
                        text_content=text_content,
                    ),
                    timeout=self.timeout,
                )
                logger.info("Email sent successfully to %s", to_email)
                return True

            except asyncio.TimeoutError:
                logger.warning(
                    "Email send timeout for %s (attempt %d/%d)",
                    to_email,
                    attempt + 1,
                    retry_count,
                )

            except aiosmtplib.SMTPAuthenticationError as e:
                logger.critical("SMTP authentication failed: %s", e)
                return False  # Don't retry on auth failure

            except aiosmtplib.SMTPException as e:
                logger.error(
                    "SMTP error sending to %s (attempt %d/%d): %s",
                    to_email,
                    attempt + 1,
                    retry_count,
                    type(e).__name__,
                )

            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Unexpected error sending email to %s: %s: %s",
                    to_email,
                    type(e).__name__,
                    str(e),
                )

            # Exponential backoff between retries (except on last attempt)
            if attempt < retry_count - 1:
                wait_time = self.retry_backoff**attempt
                logger.debug("Retrying in %ss...", wait_time)
                await asyncio.sleep(wait_time)

        logger.error("Failed to send email to %s after %d attempts", to_email, retry_count)
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
        # Create MIME multipart message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_address}>"
        message["To"] = to_email

        now_utc = datetime.now(timezone.utc)
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
        except Exception as e:  # noqa: BLE001
            logger.error("SMTP connection error: %s: %s", type(e).__name__, e)
            raise

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
        pattern = (
            r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        )
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
        text = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(
            r"<style[^>]*>.*?</style>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = (
            text.replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
        )

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()


# Singleton instance
email_client = EmailClient()
