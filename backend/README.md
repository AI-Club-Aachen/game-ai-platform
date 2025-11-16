# AI Game Competition Platform – Backend

Secure backend for an AI game competition platform, built with FastAPI, PostgreSQL, SQLModel, and JWT authentication. It provides robust user management, email‑based verification and password resets, and role‑based access control, with a clean layered architecture (HTTP adapters → services → repositories → core/infrastructure).

## Features

- User registration with email verification (default role: `guest`)
- Email verification with secure tokens and configurable expiry
- Password reset via email with secure tokens
- JWT‑based authentication for API access
- Role‑based access control (`guest`, `user`, `admin`)
- Password hashing with bcrypt and strong password validation
- Async email delivery via SMTP with retry/backoff and environment‑aware behavior (log‑only in development)
- Strong typing with SQLModel and Pydantic for models and schemas
- PostgreSQL database with Alembic migrations
- Docker Compose setup for backend, PostgreSQL, and Redis
- Rate limiting with SlowAPI (per‑endpoint quotas)
- Centralized logging and structured error handling
- Security middleware (CORS, security headers, HSTS in production)

## Environment and configuration behavior

The backend uses an `ENVIRONMENT` setting (`development`, `staging`, `production`) to toggle behavior without changing code. SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`) are optional in development but required in staging/production via configuration validation. Two helpers on `Settings` expose `smtp_configured` (all SMTP fields present) and `smtp_required` (true in staging/production, false in development).

### Local development (no SMTP required)

In local development (`ENVIRONMENT=development`), SMTP is not required: the app boots and all auth flows work without a mail server. The `EmailClient` reads SMTP configuration from settings and caches flags like `smtp_configured` and `is_development` for runtime decisions.

- If SMTP is not configured and the environment is development, `send_email`:
  - Does not attempt an SMTP connection.
  - Logs a warning that SMTP is not configured.
  - Logs the recipient, subject, and full HTML content of the email.
  - Returns `True` so registration and password‑reset flows behave as if the email was sent.

### Staging/production behavior

In environments where SMTP is required and configured (staging/production), `EmailClient.send_email`:

- Validates inputs (addresses, subject, HTML).
- Builds a MIME multipart message (text + HTML).
- Connects to SMTP with TLS, authenticates, and sends the message.
- Applies retry/backoff on transient failures.
- Logs timeouts and SMTP errors, failing securely if delivery is impossible.

Deployments in staging/production enforce full SMTP configuration at startup, so misconfigured email causes a fast failure rather than silent breakage of verification/password‑reset flows.

Local developers get a frictionless setup: they only need DB/JWT/CORS environment variables; all emails (verification and password reset) are visible in logs and links can be copy‑pasted for manual testing.

## Setup

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.11+
- PostgreSQL 16+ (included in Docker)
- Redis (included in Docker)

### Docker setup (recommended)

1. Set environment variables (optional, can also be in `.env`):

   ```
   export JWT_SECRET_KEY="your-secure-secret-key-here"
   export ENVIRONMENT="development"
   ```

2. Start services:

   ```
   docker-compose up --build
   ```

The API will be available at `http://localhost:8000`.

### Local development with `uv`

1. Install `uv`:

   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Create and activate virtual environment:

   ```
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```
   uv pip install -r requirements.txt
   ```

4. Set up environment variables:

   ```
   cp .env.example .env
   # Edit .env with your configuration (JWT, DB, CORS, ENVIRONMENT, SMTP, etc.)
   ```

5. Run migrations:

   ```
   alembic upgrade head
   ```

6. Start the server:

   ```
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Database migrations

Migrations run automatically on startup in Docker. To manually manage them:

**Generate migration:**

```
docker-compose exec backend alembic revision --autogenerate -m "description"
```

**Apply migrations:**

```
docker-compose exec backend alembic upgrade head
```

**Rollback migration:**

```
docker-compose exec backend alembic downgrade -1
```

## API endpoints

For full API documentation:

- Local: `http://localhost:8000/docs` (when `ENVIRONMENT=development`)
- Scalar: `https://registry.scalar.com/@aica/apis/ai-game-competition-platform/latest?format=preview`

## User roles

### Guest (default)

- Read‑only access to public content.
- Cannot upload models or participate in matches.
- Must be promoted to `user` by an admin.

### User

- Can upload and manage AI models.
- Can participate in competitions.
- Can view leaderboards and matches.

### Admin

- Full platform control.
- User management and role changes.
- Game engine and platform configuration.
- Match management and debugging.

## Configuration

Create `.env` from `.env.example` and set all parameters accordingly. Key settings:

- `ENVIRONMENT`: `development`, `staging`, or `production`.
- `DATABASE_URL`: PostgreSQL connection string.
- `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_HOURS`.
- `ALLOW_ORIGINS`: CORS origins for your frontend.
- SMTP:
  - Required in staging/production: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`.
  - Optional in development (emails are logged instead of sent).

## Creating first admin

Connect to the database and run:

```
UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';
```

Or using Docker:

```
docker-compose exec db psql -U postgres -d gameai \
  -c "UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';"
```

## Email verification & password reset

### Registration flow

1. User registers → account created with `role=guest` and `email_verified=false`.
2. `AuthService` generates an email‑verification token (hashed in DB with expiry).
3. `EmailNotificationService` sends a verification email with a secure link.
4. User clicks the link → token is verified → user is marked `email_verified=true`.
5. User can now log in and be promoted to `user`/`admin` as needed.

### Password reset flow

1. User requests a password reset → a reset token is generated and stored (hashed) with expiry.
2. `EmailNotificationService` sends a reset link via email.
3. User clicks the link → supplies a new password → token is verified and invalidated.
4. Password is updated (with validation and bcrypt hashing) and the reset token fields are cleared.

## Security notes

- Always change `JWT_SECRET_KEY` in production and keep it secret.
- Use strong passwords and consider enforcing length/complexity via `validate_password_strength`.
- Keep dependencies updated and rebuild images regularly.
- Enable HTTPS in production (TLS termination via reverse proxy or load balancer).
- Configure CORS to only allow your trusted frontend origins.
- The app sets security headers (HSTS, CSP, X‑Frame‑Options, etc.) and hides server details by default.

## Project structure

The backend is organized into clear layers so that HTTP, business logic, and persistence stay decoupled and easy to test:

- `api/routes`: Thin HTTP adapters (FastAPI routers). They:
  - Parse and validate requests.
  - Call services.
  - Translate domain exceptions into HTTP responses and status codes.

- `api/services`: Application services (e.g. auth, user, email notifications). They:
  - Implement use‑cases like “register user”, “login”, “change password”, “send verification email”.
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
