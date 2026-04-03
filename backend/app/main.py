"""FastAPI application with comprehensive security configuration and rate limiting"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import Response

from app.api.routes import agents, auth, email, jobs, matches, submissions, users
from app.core.config import settings
from scripts.seed_db import seed


# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Rate limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=["500/hour", "30/minute"],
)


def _apply_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    """Mirror CORS headers on error responses so browsers can read backend failures."""
    origin = request.headers.get("origin")
    if not origin:
        return response

    if "*" in settings.ALLOW_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in settings.ALLOW_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events for startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENVIRONMENT} mode")

    if os.getenv("SEED_DB") == "true":
        logger.info("SEED_DB is set to true. Running database seed script...")
        await asyncio.to_thread(seed)

    if settings.is_production and settings.BYPASS_EMAIL_VERIFICATION:
        logger.warning("Email verification is enabled in production mode")
    try:
        redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8")
        logger.info(f"Redis connected for rate limiting: {settings.REDIS_URL}")
    except Exception:
        logger.exception("Failed to connect to Redis")
        logger.warning("Rate limiting running with memory backend fallback")
        redis = None

    # Ensure upload directories exist
    try:
        submissions_dir = Path(settings.SUBMISSIONS_DIR)
        submissions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Submissions directory ensured: {submissions_dir.absolute()}")
    except PermissionError:
        logger.exception(f"Failed to create submissions directory '{settings.SUBMISSIONS_DIR}'")

    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down application")
        if redis is not None:
            try:
                await redis.close()
            except Exception:
                logger.exception("Failed to close Redis connection")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI Game Competition Platform Backend with secure authentication and rate limiting",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# Add rate limiter to app state
app.state.limiter = limiter

# Add slowapi middleware
app.add_middleware(SlowAPIMiddleware)

# Trusted Host Middleware
allowed_hosts = [
    "localhost",
    "127.0.0.1",
    "::1",  # IPv6 localhost
    "backend",  # Allow docker internal networking
]

for origin in settings.ALLOW_ORIGINS:
    domain = origin.replace("http://", "").replace("https://", "").split(":")[0]
    if domain not in allowed_hosts:
        allowed_hosts.append(domain)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
    www_redirect=True,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)


# Custom middleware for security headers
@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add security headers to all responses"""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    else:
        # Development: Allow CDN resources for Swagger UI and ReDoc
        response.headers["Strict-Transport-Security"] = "max-age=3600; includeSubDomains"
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    response.headers["Content-Security-Policy"] = csp
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), magnetometer=(), gyroscope=(), accelerometer=()"
    )

    if "server" in response.headers:
        del response.headers["server"]

    return response


# Exception handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors"""
    client_host = request.client.host if request.client is not None else "unknown"  # [web:106][web:113]
    logger.warning(f"Rate limit exceeded for {client_host}: {exc.detail}")
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."},
    )
    return _apply_cors_headers(request, response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors"""
    if settings.is_production:
        client_host = request.client.host if request.client is not None else "unknown"  # [web:106][web:113]
        logger.warning(f"Validation error from {client_host}: {exc}")
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": "Invalid request data"},
        )
        return _apply_cors_headers(request, response)
    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors()},
    )
    return _apply_cors_headers(request, response)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors"""
    logger.exception(f"Unhandled exception: {exc}")
    if settings.is_production:
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
        return _apply_cors_headers(request, response)
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )
    return _apply_cors_headers(request, response)


# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(email.router, prefix=f"{settings.API_V1_PREFIX}/email", tags=["Email"])
app.include_router(submissions.router, prefix=f"{settings.API_V1_PREFIX}/submissions", tags=["Submissions"])
app.include_router(agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["Agents"])
app.include_router(matches.router, prefix=f"{settings.API_V1_PREFIX}/matches", tags=["Matches"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_PREFIX}/jobs", tags=["Jobs"])


# Health check endpoint
@app.get("/health", tags=["Health"])
@limiter.exempt
async def health_check() -> dict:
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get("/", tags=["Root"])
@limiter.exempt
async def root() -> dict:
    """Root endpoint with API information"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "docs": "/docs" if settings.docs_enabled else None,
        "health": "/health",
    }
