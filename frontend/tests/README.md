# Playwright Integration Tests

## Directory Structure

We use a role-based directory structure to organize tests:

```
tests/
├── setup/              # Authentication setup scripts
│   ├── auth.setup.ts   # Standard user login/registration
│   ├── admin.setup.ts  # Admin user promotion & login
│   └── teardown.ts     # Global cleanup
├── e2e/
│   ├── guest/          # Public routes (Login, Landing)
│   ├── user/           # Protected routes (Dashboard, Profile)
│   └── admin/          # Admin-only features
└── utils/              # Shared helpers (db access, etc.)
```

## Authentication Strategy

Test authentication is handled globally to save time and ensure robustness.

1.  **Global Setup (`tests/setup/*.setup.ts`)**:
    *   Runs **once** before tests.
    *   Creates/Verify a test user in the DB.
    *   Saves the browser state (cookies/storage) to `playwright/.auth/*.json`.
2.  **Test Execution**:
    *   Tests reuse this state via `playwright.config.ts` projects (`chromium`, `admin`).
    *   Tests start *already logged in*.

## Adding New Tests

1.  **Identify the Role**:
    *   **Guest**: Place in `e2e/guest/`. Use `test.use({ storageState: { cookies: [], origins: [] } })` if you need to ensure no session.
    *   **Standard User**: Place in `e2e/user/`. These use the default `chromium` project state.
    *   **Admin**: Place in `e2e/admin/`. Add `// Uses admin auth` comment.

2.  **Naming**: Use `*.spec.ts` for test files.

## Running Tests

*   Run all: `npx playwright test`
*   Run specific role: `npx playwright test --project=admin`
*   Debug: `npx playwright test --ui`
