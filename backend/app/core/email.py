"""Email service with security best practices"""

import asyncio
import logging
from typing import Optional
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Async email service using aiosmtplib.
    Handles secure SMTP connection with TLS and timeout handling.
    """

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_address = settings.SMTP_FROM_ADDRESS
        self.from_name = settings.SMTP_FROM_NAME
        self.timeout = 10  # seconds

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        retry_count: int = 3,
    ) -> bool:
        """
        Send email with retry logic and security best practices.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text fallback (auto-generated if None)
            retry_count: Number of retries on failure

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not text_content:
            text_content = self._strip_html_to_text(html_content)

        for attempt in range(retry_count):
            try:
                await self._send_via_smtp(to_email, subject, html_content, text_content)
                logger.info(f"Email sent successfully to {to_email}")
                return True

            except asyncio.TimeoutError:
                logger.warning(
                    f"Email send timeout for {to_email} (attempt {attempt + 1}/{retry_count})"
                )
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except aiosmtplib.SMTPException as e:
                logger.error(
                    f"SMTP error sending to {to_email} (attempt {attempt + 1}/{retry_count}): {e}"
                )
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Unexpected error sending email to {to_email}: {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.error(f"Failed to send email to {to_email} after {retry_count} attempts")
        return False

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> None:
        """
        Internal method to send email via SMTP.
        Handles connection, authentication, and message sending.
        """
        # Create message with both plain text and HTML parts
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_address}>"
        message["To"] = to_email

        # Attach plain text first (fallback for email clients)
        part1 = MIMEText(text_content, "plain")
        message.attach(part1)

        # Attach HTML (preferred by modern email clients)
        part2 = MIMEText(html_content, "html")
        message.attach(part2)

        # Send via SMTP with TLS
        async with aiosmtplib.SMTP(
            hostname=self.smtp_host,
            port=self.smtp_port,
            use_tls=self.smtp_use_tls,
            timeout=self.timeout,
        ) as smtp:
            await smtp.login(self.smtp_username, self.smtp_password)
            await smtp.send_message(message)

    @staticmethod
    def _strip_html_to_text(html: str) -> str:
        """Convert HTML to plain text (simple regex approach)"""
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()


# Singleton instance
email_service = EmailService()
