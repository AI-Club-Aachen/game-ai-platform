"""Email client with SMTP transport, retry logic, and environment-aware behavior."""

import asyncio
import logging
import re
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime, make_msgid

import aiosmtplib

from app.core.config import settings


logger = logging.getLogger(__name__)

MAX_EMAIL_LENGTH = 254
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 2  # exponential backoff multiplier


class EmailClient:
    """Low-level SMTP email client with retry logic and environment-aware behavior."""

    def __init__(self) -> None:
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS

        self.from_address = settings.SMTP_FROM_ADDRESS or "dev-noreply@example.local"
        self.from_name = settings.SMTP_FROM_NAME

        self.timeout = DEFAULT_TIMEOUT
        self.max_retries = DEFAULT_MAX_RETRIES
        self.retry_backoff = DEFAULT_RETRY_BACKOFF

        self.smtp_configured = settings.smtp_configured
        self.smtp_required = settings.smtp_required
        self.is_development = settings.is_development

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
        retry_count: int | None = None,
    ) -> bool:
        """Send email with automatic retry and error handling."""
        should_send, result = self._should_send_email(to_email, subject, html_content)
        if not should_send:
            return result

        if not self._validate_email(to_email):
            logger.error("Invalid email address: %s", to_email)
            return False

        if not subject or not html_content:
            logger.error("Subject and html_content are required")
            return False

        final_text_content = self._prepare_email_content(html_content, text_content)
        final_retry_count = retry_count if retry_count is not None else self.max_retries
        return await self._send_with_retry(to_email, subject, html_content, final_text_content, final_retry_count)

    def _should_send_email(self, to_email: str, subject: str, html_content: str) -> tuple[bool, bool]:
        """Determine if email should be sent based on environment settings."""
        # In development, always just log and skip sending
        if self.is_development:
            logger.warning("Development mode; email will NOT be sent, only logged.")
            logger.info("Dev email to=%s subject=%s", to_email, subject)
            logger.info("Dev email HTML content:\n%s", html_content)
            return False, True

        # If SMTP is not configured, check if it's required
        if not self.smtp_configured:
            if self.smtp_required:
                logger.critical("SMTP is required in this environment but not configured; cannot send email.")
                return False, False
            
            logger.error("SMTP not configured; skipping email send.")
            return False, False

        return True, True

    def _prepare_email_content(self, html_content: str, text_content: str | None) -> str:
        if text_content:
            return text_content
        return self._strip_html_to_text(html_content)

    async def _send_with_retry(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        retry_count: int,
    ) -> bool:
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
            except TimeoutError:
                logger.warning(
                    "Email send timeout for %s (attempt %d/%d)",
                    to_email,
                    attempt + 1,
                    retry_count,
                )
            except aiosmtplib.SMTPAuthenticationError as e:
                logger.critical("SMTP authentication failed: %s", e)
                return False
            except aiosmtplib.SMTPException as e:
                logger.exception(
                    "SMTP error sending to %s (attempt %d/%d): %s",
                    to_email,
                    attempt + 1,
                    retry_count,
                    type(e).__name__,
                )
            except Exception:
                logger.exception("Unexpected error sending email to %s", to_email)
            else:
                logger.info("Email sent successfully to %s", to_email)
                return True

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
        """Send an email via SMTP."""
        username = self.smtp_username
        password = self.smtp_password
        if username is None or password is None:
            logger.critical("SMTP credentials not configured; cannot send email.")
            raise RuntimeError("SMTP credentials not configured")

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_address}>"
        message["To"] = to_email

        now_utc = datetime.now(UTC)
        message["Date"] = format_datetime(now_utc)
        message["Message-ID"] = make_msgid(domain=self.smtp_host)

        part1 = MIMEText(text_content, "plain", "utf-8")
        message.attach(part1)

        part2 = MIMEText(html_content, "html", "utf-8")
        message.attach(part2)

        try:
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls,
                timeout=self.timeout,
            ) as smtp:
                await smtp.login(username, password)
                await smtp.send_message(message)
        except aiosmtplib.SMTPAuthenticationError:
            logger.critical("SMTP authentication failed - check credentials")
            raise
        except Exception:
            logger.exception("SMTP connection error")
            raise

    @staticmethod
    def _validate_email(email: str) -> bool:
        """Validate email format."""
        if not email or len(email) > MAX_EMAIL_LENGTH:
            return False

        pattern = (
            r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        )
        return bool(re.match(pattern, email))

    @staticmethod
    def _strip_html_to_text(html: str) -> str:
        """Convert HTML to plain text using regex."""
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

        text = re.sub(r"<[^>]+>", "", text)

        text = (
            text.replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
        )

        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()


email_client = EmailClient()
