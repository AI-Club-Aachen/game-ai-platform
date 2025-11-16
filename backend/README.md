# AI Game Competition Platform - Backend

Secure user management system with FastAPI, PostgreSQL, JWT authentication, email verification, and role-based access control.

## Features

* User registration with email verification (default role: guest)
* Email verification with secure tokens (24h expiry)
* Password reset via email with secure tokens (1h expiry)
* JWT-based authentication (24h token expiration)
* Role-based access control (guest, user, admin)
* Password hashing with bcrypt
* Async email sending via SMTP (netcup integration)
* Strong typing with SQLModel and Pydantic
* PostgreSQL database
* Docker Compose for local development
* Rate limiting with slowapi
* Redis caching support
* Comprehensive logging
* Alembic for database migrations



## Setup

### Prerequisites

* Docker & Docker Compose (recommended)
* Python 3.11+
* PostgreSQL 16+ (included in Docker)
* Redis (included in Docker)

### Docker Setup (Recommended)

1. Set environment variables (optional, can also be in `.env`):

   ```bash
   export JWT_SECRET_KEY="your-secure-secret-key-here"
    ```

2.  Start services:

    ```bash
    docker-compose up --build
    ```

The API will be available at `http://localhost:8000`.

### Local Development with `uv`

1.  Install `uv`:

    ```bash
    curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
    ```

2.  Create and activate virtual environment:

    ```bash
    uv venv
    source .venv/bin/activate # On Windows: .venv\Scripts\activate
    ```

3.  Install dependencies:

    ```bash
    uv pip install -r requirements.txt
    ```

4.  Set up environment variables:

    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```

5.  Run migrations:

    ```bash
    alembic upgrade head
    ```

6.  Start the server:

    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

## Database Migrations

Migrations run automatically on startup. To manually manage:

**Generate migration**
```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

**Apply migrations**

```bash
docker-compose exec backend alembic upgrade head
```

**Rollback migration**

```bash
docker-compose exec backend alembic downgrade -1
```

## API Endpoints

### Authentication

  * `POST /api/v1/auth/register` - Register new user (guest role)

  * `POST /api/v1/auth/login` - Login and receive JWT token

### Users

  * `GET /api/v1/users/me` - Get current user profile

  * `PATCH /api/v1/users/me` - Update own profile/password

  * `GET /api/v1/users/{user_id}` - Admin: Get user by ID

  * `PATCH /api/v1/users/{user_id}/role` - Admin: Update user role

  * `POST /api/v1/users/{user_id}/reset-password` - Admin: Reset user password

### Email Verification

* `POST /api/v1/email/send-verification` - Resend verification email
  * Requires: Bearer token

* `POST /api/v1/email/verify` - Verify email with token
  * Request: `token`
  * Response: User object (email_verified: true)

### Password Reset

* `POST /api/v1/email/request-password-reset` - Request password reset
  * Request: `email`

* `POST /api/v1/email/reset-password` - Reset password with token
  * Request: `token`, `new_password`


## User Roles

### Guest (default)

  * Read-only access to public content

  * Cannot upload models or participate in matches

  * Must be promoted to user by admin

### User

  * Can upload and manage AI models

  * Can participate in competitions

  * Can view all leaderboards and matches

### Admin

  * Full platform control

  * User management and role changes

  * Game engine and platform configuration

  * Match management and debugging

## Configuration

Create `.env` from `.env.example` and set:
```bash
SMTP_HOST=mx2f17.netcup.net
SMTP_PORT=465
SMTP_USERNAME=your-netcup-email
SMTP_PASSWORD=your-netcup-password
SMTP_FROM_ADDRESS=no-reply@ai-club-aachen.com
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=60
```

Generate secure JWT key:
```bash
openssl rand -hex 32
```



## Creating First Admin

Connect to the database and run:

```sql
UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';
```

Or using Docker:

```bash
docker-compose exec db psql -U postgres -d gameai -c "UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';"
```

## Email Verification & Password Reset

### Registration Flow
1. User registers → account created as `email_verified=false`
2. Verification email sent with secure token (24h expiry)
3. User clicks link → token verified → account activated
4. User can now login

### Password Reset Flow
1. User requests reset → token sent via email (1h expiry)
2. User clicks link → enters new password → token invalidated


## Security Notes

  * Always change `JWT_SECRET_KEY` in production

  * Use strong passwords (minimum 8 characters)

  * Keep dependencies updated

  * Enable HTTPS in production

  * Configure CORS appropriately for your frontend

## Project Structure

```text
backend/
├── app/
│ ├── api/
│ │ ├── deps.py # Dependencies (auth, DB session)
│ │ └── routes/
│       ├── auth.py            # Registration & login
│       ├── email.py           # Email verification & password reset
│       └── users.py           # User management
│ ├── core/
│ │   ├── config.py            # Environment settings
│ │   ├── security.py          # JWT & password hashing
│ │   ├── email.py             # Email service (SMTP)
│ │   └── tokens.py            # Token generation & verification
│ ├── db/
│ │ ├── base.py # SQLModel base
│ │ ├── connection.py # Database engine
│ │ └── session.py # Session dependency
│ ├── models/ # SQLModel database models
│ ├── schemas/
│ │   ├── auth.py              # Auth schemas
│ │   ├── email.py             # Email verification schemas
│ │   └── user.py              # User schemas
│ └── main.py # FastAPI application
├── alembic/ # Database migrations
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```