"""Application-level email notification service (verification, password reset)."""

import logging

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
        brand = getattr(settings, "PROJECT_NAME", "AI Game Platform")

        html_content = f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <title>Verify your email</title>
          </head>
          <body style="margin:0; padding:0; background-color:#121212;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#121212;">
              <tr>
                <td align="center" style="padding:24px 16px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px; background-color:#1e1e1e; border:1px solid #333333;">
                    <!-- Header -->
                    <tr>
                      <td style="padding:24px;">
                        <div style="font-family:'Lato', Arial, sans-serif; font-size:24px; font-weight:700; color:#ffffff; margin-bottom:4px;">
                          {self._escape_html(brand)}
                        </div>
                        <div style="font-family:'Lato', Arial, sans-serif; font-size:16px; font-weight:600; color:#ffffff;">
                          Welcome, {self._escape_html(username)} 👋
                        </div>
                      </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                      <td style="padding:0 24px;">
                        <hr style="border:none; border-top:1px solid #333333; margin:0;">
                      </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                      <td style="padding:20px 24px 24px;">
                        <p style="margin:0 0 16px; font-family:'Lato', Arial, sans-serif; font-size:14px; line-height:1.6; color:#cccccc;">
                          Thanks for signing up! Please confirm your email address to activate your account.
                        </p>

                        <!-- CTA -->
                        <div style="margin:24px 0;">
                          <a href="{verify_url}"
                             style="
                               display:inline-block;
                               text-decoration:none;
                               font-family:'Lato', Arial, sans-serif;
                               font-size:14px;
                               font-weight:600;
                               color:#ffffff;
                               padding:12px 24px;
                               background:linear-gradient(90deg, #00D98B 0%, #00A6FF 100%);
                               border-radius:0;
                             ">
                            Verify email
                          </a>
                        </div>

                        <!-- Fallback link -->
                        <p style="margin:0 0 8px; font-family:'Lato', Arial, sans-serif; font-size:12px; color:#cccccc;">
                          Or copy this link:
                        </p>
                        <div style="
                          font-family:'Lato', Arial, sans-serif;
                          font-size:12px;
                          color:#ffffff;
                          background-color:#121212;
                          border:1px solid #333333;
                          padding:10px 12px;
                          word-break:break-all;
                        ">
                          {verify_url}
                        </div>

                        <p style="margin:16px 0 0; font-family:'Lato', Arial, sans-serif; font-size:12px; color:#cccccc;">
                          This verification link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.
                        </p>
                      </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                      <td style="padding:16px 24px 24px;">
                        <hr style="border:none; border-top:1px solid #333333; margin:0 0 12px;">
                        <p style="margin:0; font-family:'Lato', Arial, sans-serif; font-size:12px; color:#7f8c8d;">
                          If you didn’t create this account, you can safely ignore this email.
                        </p>
                      </td>
                    </tr>
                  </table>

                  <p style="margin:12px 0 0; font-family:'Lato', Arial, sans-serif; font-size:11px; color:#666666;">
                    © {self._escape_html(brand)}
                  </p>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """.strip()

        text_content = f"""
        {brand}

        Welcome, {username}!

        Confirm your email to activate your account:

        {verify_url}

        This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.

        If you didn’t create this account, ignore this email.
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
        brand = getattr(settings, "PROJECT_NAME", "AI Game Platform")

        html_content = f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <title>Password reset</title>
          </head>
          <body style="margin:0; padding:0; background-color:#121212;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#121212;">
              <tr>
                <td align="center" style="padding:24px 16px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px; background-color:#1e1e1e; border:1px solid #333333;">
                    <!-- Header -->
                    <tr>
                      <td style="padding:24px;">
                        <div style="font-family:'Lato', Arial, sans-serif; font-size:24px; font-weight:700; color:#ffffff; margin-bottom:4px;">
                          {self._escape_html(brand)}
                        </div>
                        <div style="font-family:'Lato', Arial, sans-serif; font-size:16px; font-weight:600; color:#ffffff;">
                          Password reset requested
                        </div>
                      </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                      <td style="padding:0 24px;">
                        <hr style="border:none; border-top:1px solid #333333; margin:0;">
                      </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                      <td style="padding:20px 24px 24px;">
                        <p style="margin:0 0 16px; font-family:'Lato', Arial, sans-serif; font-size:14px; line-height:1.6; color:#cccccc;">
                          Hi {self._escape_html(username)}, we received a request to reset your password.
                          If this was you, use the button below to choose a new password.
                        </p>

                        <!-- CTA -->
                        <div style="margin:24px 0;">
                          <a href="{reset_url}"
                             style="
                               display:inline-block;
                               text-decoration:none;
                               font-family:'Lato', Arial, sans-serif;
                               font-size:14px;
                               font-weight:600;
                               color:#ffffff;
                               padding:12px 24px;
                               background:linear-gradient(90deg, #00D98B 0%, #00A6FF 100%);
                               border-radius:0;
                             ">
                            Reset password
                          </a>
                        </div>

                        <!-- Fallback link -->
                        <p style="margin:0 0 8px; font-family:'Lato', Arial, sans-serif; font-size:12px; color:#cccccc;">
                          Or copy this link:
                        </p>
                        <div style="
                          font-family:'Lato', Arial, sans-serif;
                          font-size:12px;
                          color:#ffffff;
                          background-color:#121212;
                          border:1px solid #333333;
                          padding:10px 12px;
                          word-break:break-all;
                        ">
                          {reset_url}
                        </div>

                        <p style="margin:16px 0 0; font-family:'Lato', Arial, sans-serif; font-size:12px; color:#cccccc;">
                          This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
                        </p>
                      </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                      <td style="padding:16px 24px 24px;">
                        <hr style="border:none; border-top:1px solid #333333; margin:0 0 12px;">
                        <p style="margin:0; font-family:'Lato', Arial, sans-serif; font-size:12px; color:#7f8c8d;">
                          If you didn’t request this, you can ignore this email – your password has not been changed.
                        </p>
                      </td>
                    </tr>
                  </table>

                  <p style="margin:12px 0 0; font-family:'Lato', Arial, sans-serif; font-size:11px; color:#666666;">
                    © {self._escape_html(brand)}
                  </p>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """.strip()

        text_content = f"""
        {brand} — password reset

        Hi {username},

        We received a request to reset your password. If this was you, use the link below to choose a new password:

        {reset_url}

        This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.

        If you didn’t request this, you can ignore this email.
        """.strip()

        return await self._client.send_email(
            to_email=to_email,
            subject="Password Reset Request",
            html_content=html_content,
            text_content=text_content,
        )

    @staticmethod
    def _escape_html(text: str | None) -> str:
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
