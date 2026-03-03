# Integration Tests

This directory contains end-to-end integration tests that interact with the live backend API.

## Prerequisites

1.  **Backend Running**: The backend server must be running (normally at `http://localhost:8000`).
2.  **Dependencies**: Install the required Python packages:
    ```bash
    pip install -r tests/requirements.txt
    ```

## Configuration

The tests use environment variables for configuration. You can set these in your shell or via a `.env` file if using a runner that supports it.

-   `API_URL`: The base URL of the API (default: `http://localhost:8000/api/v1`).

### Development Mode (Recommended)

To run tests smoothly without dealing with real email verification, enable the bypass flag in your backend's `.env` (or environment):

```env
BYPASS_EMAIL_VERIFICATION=True
```

This causes the `/auth/register` endpoint to automatically verify new users, allowing the test fixtures to log in immediately.

## Running Tests

Run all integration tests using `pytest` from the root of the repository:

```bash
pytest tests/
```

To see output and print statements:
```bash
pytest tests/ -s
```

## Shared Fixtures (`conftest.py`)

A few helpful fixtures are available for use in any test within this directory:

-   `api_base_url`: Returns the configured `API_URL`.
-   `user_credentials`: Returns a dictionary with a random `username`, `email`, and `password`.
-   `verified_user_token`: Automatically registers a new user and returns their JWT access token.
-   `auth_headers`: Returns a dictionary containing the `Authorization: Bearer <token>` header, ready for use with `requests`.

## Test Suites

-   `test_submission_to_agent.py`: Verifies the full workflow of zipping an agent, submitting it to the API, and waiting for the build process to complete.