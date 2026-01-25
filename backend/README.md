# AI Game Competition Platform – Backend

Secure backend for an AI game competition platform, built with FastAPI, PostgreSQL, SQLModel, and JWT authentication.

## Table of Contents

### Getting Started
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development (uv)](#local-development-uv)
- [Common Tasks](#common-tasks)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)

### Architecture & Details
- [Features](#features)
- [Environment and Configuration Behavior](#environment-and-configuration-behavior)
- [User Roles](#user-roles)
- [Email Verification & Password Reset](#email-verification--password-reset)
- [Testing](#testing)
- [Security Notes](#security-notes)
- [Project Structure](#project-structure)

---

## Getting Started

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.12+
- PostgreSQL 16+ (included in Docker)
- Redis (included in Docker)

### Quick Start (Docker)

1. **Frontend**:
   ```bash
   cd frontend
   pnpm install
   pnpm run dev
   # Access at http://localhost:3000
   ```

2. **Backend (Development)**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env: set ENVIRONMENT=development, JWT_SECRET_KEY, etc.
   
   # Start development services (PostgreSQL on :5432, Redis on :6379, Backend on :8000)
   docker-compose up --build
   # API at http://localhost:8000
   ```

### Local Development (uv)

1. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Setup**:
   ```bash
   cd backend
   uv venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   uv sync
   ```

3. **Run**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Common Tasks

**Create Admin User**:
```bash
docker-compose exec db psql -U postgres -d gameai -c "UPDATE users SET role = 'ADMIN' WHERE email = 'admin2@deutmail.com';"
```

**Run Tests**:
```bash
# First, start test database and Redis (on ports 5433 and 6380)
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Stop test services when done
docker-compose -f docker-compose.test.yml down
```

**Code Quality** (required to pass CI/CD pipeline):
```bash
# Lint with ruff
uv run lint

# Auto-fix linting issues
uv run lint --fix

# Format code with ruff
uv run format

# Type check with mypy
uv run type-check

# Run all checks
uv run checks-all
```

**Database Migrations**:
```bash
# Generate migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

### Configuration

Create `.env` from `.env.example` and set:

- `ENVIRONMENT`: `development`, `staging`, or `production`
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_HOURS`
- `ALLOW_ORIGINS`: CORS origins for your frontend
- SMTP (optional in development, required in staging/production):
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`

### API Documentation

- Local: `http://localhost:8000/docs` (when `ENVIRONMENT=development`)
- Scalar: `https://registry.scalar.com/@aica/apis/ai-game-competition-platform/latest?format=preview`

---

## Architecture & Details

### Features

- User registration with email verification (default role: `guest`)
- Profile picture support (upload and update via API)
- Email verification with secure tokens and configurable expiry
- Password reset via email with secure tokens
- JWT-based authentication for API access
- Role-based access control (`guest`, `user`, `admin`)
- Password hashing with bcrypt and strong password validation
- Async email delivery via SMTP with retry/backoff and environment-aware behavior (log-only in development)
- Strong typing with SQLModel and Pydantic for models and schemas
- PostgreSQL database with Alembic migrations
- Docker Compose setup for backend, PostgreSQL, and Redis
- Rate limiting with SlowAPI (per-endpoint and global quota)
- Centralized logging and structured error handling
- Security middleware (CORS, security headers, HSTS in production)

### Environment and Configuration Behavior

The backend uses an `ENVIRONMENT` setting (`development`, `staging`, `production`) to toggle behavior without changing code. SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`) are optional in development but required in staging/production via configuration validation.

#### Local Development (no SMTP required)

In local development (`ENVIRONMENT=development`), SMTP is not required: the app boots and all auth flows work without a mail server. The `EmailClient` reads SMTP configuration from settings and caches flags like `smtp_configured` and `is_development` for runtime decisions.

- If SMTP is not configured and the environment is development, `send_email`:
  - Does not attempt an SMTP connection.
  - Logs a warning that SMTP is not configured.
  - Logs the recipient, subject, and full HTML content of the email.
  - Returns `True` so registration and password‑reset flows behave as if the email was sent.

#### Staging/Production Behavior

In environments where SMTP is required and configured (staging/production), `EmailClient.send_email`:

- Validates inputs (addresses, subject, HTML).
- Builds a MIME multipart message (text + HTML).
- Connects to SMTP with TLS, authenticates, and sends the message.
- Applies retry/backoff on transient failures.
- Logs timeouts and SMTP errors, failing securely if delivery is impossible.

Deployments in staging/production enforce full SMTP configuration at startup, so misconfigured email causes a fast failure rather than silent breakage of verification/password‑reset flows.

### User Roles

The backend defines three roles using specific enums. You can retrieve the list of available roles via the `GET /users/roles` endpoint (authenticated).

#### Guest (default)

- Read-only access to public content.
- Cannot upload models or participate in matches.
- Must be promoted to `user` by an admin.

#### User

- Can upload and manage AI models.
- Can participate in competitions.
- Can view leaderboards and matches.

#### Admin

- Full platform control.
- User management and role changes.
- Game engine and platform configuration.
- Match management and debugging.

### Email Verification & Password Reset

#### Registration Flow

1. User registers → account created with `role=guest` and `email_verified=false`.
2. `AuthService` generates an email‑verification token (hashed in DB with expiry).
3. `EmailNotificationService` sends a verification email with a secure link.
4. User clicks the link → token is verified → user is marked `email_verified=true`.
5. User can now log in and be promoted to `user`/`admin` as needed.

#### Password Reset Flow

1. User requests a password reset → a reset token is generated and stored (hashed) with expiry.
2. `EmailNotificationService` sends a reset link via email.
3. User clicks the link → supplies a new password → token is verified and invalidated.
4. Password is updated (with validation and bcrypt hashing) and the reset token fields are cleared.

### Testing

The backend ships with async end-to-end tests for auth, email verification, and user/role management, built with `pytest` and `pytest-anyio`.

#### Docker Compose Files

The project uses separate Docker Compose files for different purposes:

- **`docker-compose.yml`** - **Development only**
  - Services: `db` (PostgreSQL on port 5432), `redis` (port 6379), `backend` (port 8000)
  - Use for: Local development and running the application
  - Start with: `docker-compose up --build`

- **`docker-compose.test.yml`** - **Testing only**
  - Services: `test-db` (PostgreSQL on port 5433), `test-redis` (port 6380)
  - Use for: Running the test suite with isolated test databases
  - Start with: `docker-compose -f docker-compose.test.yml up -d`
  - Stop with: `docker-compose -f docker-compose.test.yml down`

> **Note**: Test services run on different ports (5433, 6380) to avoid conflicts with development services.

#### Test Suite Architecture

The test suite:

- Spins up the FastAPI app in‑process and talks to it via an async HTTP client. 
- Uses a dedicated Postgres test database and overrides the app's DB session via `tests/conftest.py`.
- Injects a fake email client so verification and reset emails are captured in memory instead of hitting SMTP.
- Uses `tests/utils.py` for generating random test data (users, emails, strong passwords) to ensure robust and independent test cases.

Test environment variables are configured in `pytest.ini`.

### Security Notes

- Always change `JWT_SECRET_KEY` in production and keep it secret.
- Use strong passwords and consider enforcing length/complexity via `validate_password_strength`.
- Keep dependencies updated and rebuild images regularly.
- Enable HTTPS in production (TLS termination via reverse proxy or load balancer).
- Configure CORS to only allow your trusted frontend origins.
- The app sets security headers (HSTS, CSP, X‑Frame‑Options, etc.) and hides server details by default.

### Project Structure

The backend is organized into clear layers so that HTTP, business logic, and persistence stay decoupled and easy to test:

- `api/routes`: Thin HTTP adapters (FastAPI routers). They:
  - Parse and validate requests.
  - Call services.
  - Translate domain exceptions into HTTP responses and status codes.

- `api/services`: Application services (e.g. auth, user, email notifications). They:
  - Implement use‑cases like "register user", "login", "change password", "send verification email".
  - Coordinate repositories, token helpers, security utilities, and the email client.
  - Contain orchestration logic, but no direct HTTP or SQL.

- `api/repositories`: Data access layer. It:
  - Encapsulates all SQLModel queries and transaction handling.
  - Exposes a small, typed API (e.g. `UserRepository.get_by_id`, `list_users`, `save`, `delete`).
  - Shields the rest of the codebase from SQL details.

- `core`: Cross‑cutting infrastructure and policies. It includes:
  - Configuration (`Settings`) with `ENVIRONMENT`, DB, JWT, SMTP, and CORS.
  - Security utilities (password hashing, JWT creation/verification, secure comparisons).
  - Token utilities (generation, hashing, expiry logic).
  - A low‑level `EmailClient` that handles SMTP, retries, and environment‑aware behavior.

- `models`, `schemas`, `db`:
  - `models`: SQLModel entities that map to database tables (e.g. `User` with roles and token fields).
  - `schemas`: Pydantic models that define the public API contracts.
  - `db`: Engine and session setup plus Alembic integration.

This layout reflects the runtime architecture:

- Routes only know about HTTP and services.
- Services express the domain logic and can be tested without FastAPI or a database.
- Repositories isolate persistence concerns.
- Core holds shared infrastructure that can be reused by multiple services.

The result is a backend that is easy to extend with new domains (games, matches, leaderboards) while keeping authentication and user management clean, testable, and secure.
