# AI Game Competition Platform - Backend

Secure user management system with FastAPI, PostgreSQL, JWT authentication, and role-based access control.

## Features

* User registration (default role: guest)

* JWT-based authentication (24h expiration)

* Role-based access control (guest, user, admin)

* Password hashing with bcrypt

* Strong typing with SQLModel and Pydantic

* PostgreSQL database

* Docker support

## Setup

### Prerequisites

* Python 3.11+

* PostgreSQL 16+ (or use Docker)

* `uv` (optional, for local development)

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

Create a new migration:

```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback migration:

```bash
alembic downgrade -1
```

### Initial Migration

If starting from scratch:

```bash
alembic revision --autogenerate -m "Initial user model"
alembic upgrade head
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

## Creating First Admin

Connect to the database and run:

```sql
UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';
```

Or using Docker:

```bash
docker-compose exec db psql -U postgres -d gameai -c "UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';"
```

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
│ │ └── routes/ # Route handlers
│ ├── core/
│ │ ├── config.py # Settings
│ │ └── security.py # JWT & password hashing
│ ├── db/
│ │ ├── base.py # SQLModel base
│ │ ├── connection.py # Database engine
│ │ └── session.py # Session dependency
│ ├── models/ # SQLModel database models
│ ├── schemas/ # Pydantic request/response schemas
│ └── main.py # FastAPI application
├── alembic/ # Database migrations
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Required `__init__.py` Files

Create empty `__init__.py` files in the following directories to make them Python packages:

```text
backend/app/__init__.py
backend/app/core/__init__.py
backend/app/db/__init__.py
backend/app/models/__init__.py
backend/app/schemas/__init__.py
backend/app/api/__init__.py
backend/app/api/routes/__init__.py
```
