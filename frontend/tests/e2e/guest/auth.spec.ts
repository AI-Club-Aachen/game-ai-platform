import { test, expect } from '@playwright/test';
import { verifyUserEmail, setEmailVerificationToken } from '../../utils/db';

test.describe('Authentication', () => {

    // This test file uses the default 'chromium' project which has the storage state loaded.
    // So 'test' here is ALREADY authenticated as the setup user.
    // If we want to test LOGIN flow specifically, we should use a clean context or browser.

    test.use({ storageState: { cookies: [], origins: [] } }); // Start with clean state for login tests

    test('should allow user to login', async ({ page }) => {
        const email = 'test-login-flow@example.com';
        const password = 'Password123!';

        // Register first ensuring user exists (or just fail if exists and try login)
        // For specialized login test, better to have a dedicated user or handle registration.

        await page.goto('/register');
        await page.fill('input[name="username"]', 'login_tester');
        await page.fill('input[name="email"]', email);
        await page.fill('input[name="password"]', password);
        await page.fill('input[name="confirmPassword"]', password);
        // Agree to terms
        await page.locator('input[type="checkbox"]').check();

        // Attempt registration
        await page.click('button[type="submit"]');

        // Handle "user already exists" scenario if needed
        // But since we want to test the happy path, we assume clean DB or unique user.
        // Making unique email:
        const uniqueEmail = `test-login-${Date.now()}@example.com`;

        // Actually, let's restart with unique email
        await page.goto('/register');
        await page.fill('input[name="username"]', `tester_${Date.now()}`);
        await page.fill('input[name="email"]', uniqueEmail);
        await page.fill('input[name="password"]', password);
        await page.fill('input[name="confirmPassword"]', password);
        // Agree to terms
        await page.locator('input[type="checkbox"]').check();

        await page.click('button[type="submit"]');

        // Wait for redirect to verify email
        await page.waitForURL('**/verify-email**');

        // Set a known verification token
        const verificationToken = '123456';
        setEmailVerificationToken(uniqueEmail, verificationToken);

        // Enter the token in the UI (assuming there is an input for the token)
        // Adjust selector based on actual UI implementation. 
        // Usually it's an input field or a set of inputs.
        // If it's a URL-based verification, we might need to visit the link.
        // But user asked for "get the email code", implying manual entry or simulating the link.

        // If we are on the verification page, look so see if we can input the code.
        // If the UI is just "Resend Email" and waiting for link click, we might need to construct the link.
        // Link format in backend: /verify-email?token=...

        // Let's assume for now we can visit the verification link directly with the token
        await page.goto(`/verify-email?token=${verificationToken}`);

        // Wait for success message or redirect
        // If successful, we should be able to login or be redirected to login/dashboard
        // Assuming after verification, we can login.

        // Now Login
        await page.goto('/login');
        await page.fill('input[name="email"]', uniqueEmail);
        await page.fill('input[name="password"]', password);
        await page.click('button[type="submit"]');

        await expect(page).toHaveURL('/dashboard');

        // Verify dashboard content
        await expect(page.locator('text=Welcome')).toBeVisible();
    });
});


