import { defineConfig, devices } from '@playwright/test';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// import dotenv from 'dotenv';
// dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
    testDir: './tests',
    /* Run tests in files in parallel */
    fullyParallel: true,
    /* Timeout for each test */
    timeout: 60000,
    /* Fail the build on CI if you accidentally left test.only in the source code. */
    forbidOnly: !!process.env.CI,
    /* Retry on CI only */
    retries: process.env.CI ? 1 : 0,
    /* Opt out of parallel tests on CI. */
    workers: process.env.CI ? 1 : undefined,
    /* Reporter to use. See https://playwright.dev/docs/test-reporters */
    reporter: 'html',
    /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
    use: {
        /* Base URL to use in actions like `await page.goto('/')`. */
        baseURL: 'http://localhost:3000',

        /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
        trace: 'on-first-retry',
    },

    /* Maximum time each assertion can take. */
    expect: {
        timeout: 10 * 1000,
    },

    /* Configure projects for major browsers */
    projects: [
        // Setup project for Standard User
        {
            name: 'setup',
            testMatch: /auth\.setup\.ts/,
            teardown: 'teardown', // Optional: Clean up user after all tests
        },
        // Setup project for Admin User
        {
            name: 'admin-setup',
            testMatch: /admin\.setup\.ts/,
        },
        // Teardown project
        {
            name: 'teardown',
            testMatch: /teardown\.ts/,
        },

        // 1. GUEST TESTS (No Auth)
        {
            name: 'guest',
            use: { ...devices['Desktop Chrome'] },
            testIgnore: ['**/admin.spec.ts', '**/protected.spec.ts'], // Ignore tests needing auth
            // Explicitly match tests that are for guests
            testMatch: ['**/auth.spec.ts', '**/landing.spec.ts'],
        },

        // 2. USER TESTS (Authenticated as Standard User)
        {
            name: 'chromium',
            use: {
                ...devices['Desktop Chrome'],
                storageState: 'tests/.auth/user.json',
            },
            dependencies: ['setup'],
            testMatch: ['**/protected.spec.ts'], // Tests that require login
        },

        // 3. ADMIN TESTS (Authenticated as Admin)
        {
            name: 'admin',
            use: {
                ...devices['Desktop Chrome'],
                storageState: 'tests/.auth/admin.json',
            },
            dependencies: ['admin-setup'],
            testMatch: ['**/e2e/admin/*.spec.ts'],
        },
    ],


    /* Run your local dev server before starting the tests */
    // webServer: {
    //   command: 'npm run start',
    //   url: 'http://127.0.0.1:3000',
    //   reuseExistingServer: !process.env.CI,
    // },
});
