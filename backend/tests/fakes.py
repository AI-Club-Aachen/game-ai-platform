# tests/fakes.py
from __future__ import annotations

import re
from typing import Any


class FakeEmailClient:
    """
    Minimal fake EmailClient for tests.

    It records all sent emails in-memory so tests can assert on them.
    """

    def __init__(self) -> None:
        # Each entry is a dict with keys: to_email, subject, html_content, text_content.
        self.sent: list[dict[str, Any]] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
        retry_count: int | None = None,
    ) -> bool:
        self.sent.append(
            {
                "to_email": to_email,
                "subject": subject,
                "html_content": html_content,
                "text_content": text_content,
            }
        )
        # Always "succeed" so higher-level flows are not blocked in tests.
        return True


def _extract_token_from_html(html: str) -> str:
    # Find the first "token=..." in any link, used for both verify and reset.
    match = re.search(r"token=([^\"&\s]+)", html)
    if not match:
        raise AssertionError("No token=... found in email HTML")
    return match.group(1)
