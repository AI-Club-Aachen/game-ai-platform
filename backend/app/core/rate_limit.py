"""Centralized, configurable rate limiting.

One shared Limiter for the whole app, keyed per actor class:
- valid worker API key  -> exempt
- authenticated user    -> JWT "sub" claim
- anonymous             -> client IP (when not disabled)

Limit strings live in Settings (RATE_LIMIT_*) and are read through
no-arg callables, so they stay configurable without code changes.
"""

import secrets
import uuid

from fastapi import Request
from slowapi import Limiter

from app.core.config import settings
from app.core.security import decode_access_token


def client_ip(request: Request) -> str:
    """Client IP for rate limiting; trusts X-Forwarded-For only when configured."""
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Right-most entry is the trusted proxy's hop.
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client is not None else "127.0.0.1"


def rate_limit_key(request: Request) -> str:
    """Rate-limit bucket key: worker (exempt) / user id / client IP."""
    api_key = request.headers.get("x-api-key")
    if api_key and secrets.compare_digest(api_key, settings.WORKER_API_KEY):
        # Worker requests exempt (unique key per request).
        return f"worker:{uuid.uuid4()}"

    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        payload = decode_access_token(token.strip())
        if payload is not None and payload.get("sub"):
            return f"user:{payload['sub']}"

    if settings.DISABLE_IP_RATE_LIMITING:
        # Shared-IP mode: no IP throttling; per-user limits apply.
        return f"anon:{uuid.uuid4()}"

    return f"ip:{client_ip(request)}"


limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=settings.REDIS_URL,
    default_limits=[lambda: settings.RATE_LIMIT_READS],
    enabled=settings.rate_limiting_active,
    in_memory_fallback_enabled=True,
)
