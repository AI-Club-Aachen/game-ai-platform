import { test, expect } from '@playwright/test';
import { verifyUserEmail, setEmailVerificationToken } from '../../utils/db';

test.describe('Authentication', () => {

    // This test file uses the default 'chromium' project which has the storage state loaded.
    // So 'test' here is ALREADY authenticated as the setup user.
    // If we want to test LOGIN flow specifically, we should use a clean context or browser.

    test.use({ storageState: { cookies: [], origins: [] } }); // Start with clean state for login tests

    test('should allow user to login', async ({ page }) => {
        // Use a dynamic user for this test to avoid conflicts with global setup
        const uniqueSuffix = Date.now().toString();
        const testUser = {
            username: `guest_auth_${uniqueSuffix}`,
            email: `guest.auth.${uniqueSuffix}@example.com`,
            password: 'ComplexPass!2024!Secure'
        };

        // 1. Registration
        await page.goto('/register');
        await page.fill('input[name="username"]', testUser.username);
        await page.fill('input[name="email"]', testUser.email);
        await page.fill('input[name="password"]', testUser.password);
        await page.fill('input[name="confirmPassword"]', testUser.password);
        await page.locator('input[type="checkbox"]').check();
        await page.click('button[type="submit"]');

        // Wait for verify page
        await page.waitForURL('**/verify-email**');

        // 2. Verify Email (Backend override)
        // Use the token helper or direct DB verification
        const verificationToken = '123456';
        setEmailVerificationToken(testUser.email, verificationToken);

        // Visit verification link
        await page.goto(`/verify-email?token=${verificationToken}`);

        // Should be redirected to login or show success (adjust based on app flow)
        // Assuming it stays on verify-email with success message or redirects
        await expect(page.getByText('Your email has been successfully verified')).toBeVisible({ timeout: 15000 });

        // 3. Login
        await page.goto('/login');
        await page.fill('input[name="email"]', testUser.email);
        await page.fill('input[name="password"]', testUser.password);
        await page.click('button[type="submit"]');

        // 4. Verify Dashboard
        await expect(page).toHaveURL('/dashboard');

        // Cleanup
        // deleteUserByEmail(testUser.email); // Optional: if we want to clean up immediately
    });
});


