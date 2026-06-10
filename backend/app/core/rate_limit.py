"""Centralized, configurable rate limiting (H-3).

One shared Limiter for the whole app, keyed per actor class:
- valid worker API key  -> exempt (per-request unique key never accumulates hits)
- authenticated user    -> JWT "sub" claim (no DB lookup)
- anonymous             -> client IP, X-Forwarded-For only when TRUST_PROXY_HEADERS=true

Per-category limit strings live in Settings (RATE_LIMIT_*) and are read through
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
            # Right-most entry is the hop appended by our own trusted proxy;
            # left entries are client-controlled and spoofable.
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client is not None else "127.0.0.1"


def rate_limit_key(request: Request) -> str:
    """Rate-limit bucket key: worker (exempt) / user id / client IP."""
    api_key = request.headers.get("x-api-key")
    if api_key and secrets.compare_digest(api_key, settings.WORKER_API_KEY):
        # Valid worker requests are exempt: a unique key per request never
        # exceeds any limit. Invalid keys fall through to IP-keyed limits.
        return f"worker:{uuid.uuid4()}"

    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        payload = decode_access_token(token.strip())
        if payload is not None and payload.get("sub"):
            return f"user:{payload['sub']}"

    if settings.DISABLE_IP_RATE_LIMITING:
        # Shared-IP (hackathon) mode: anonymous requests are not IP-throttled,
        # per-user-id limits above still apply.
        return f"anon:{uuid.uuid4()}"

    return f"ip:{client_ip(request)}"


limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=settings.REDIS_URL,
    default_limits=[lambda: settings.RATE_LIMIT_READS],
    enabled=settings.rate_limiting_active,
    in_memory_fallback_enabled=True,
)
