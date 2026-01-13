import { test as setup, expect } from '@playwright/test';
import { verifyUserEmail, deleteUserByEmail } from '../utils/db';
import { TEST_USERS } from '../utils/constants';

setup('authenticate as user', async ({ page }) => {
    const { authFile, email, password, username } = TEST_USERS.standard;

    // Cleanup potential stale state
    try {
        console.log('Cleaning up old test user...');
        deleteUserByEmail(email);
    } catch (e) {
        console.log('Cleanup failed (user might not exist), continuing:', e);
    }

    // Perform login (it should fail now, so we can test registration)
    // OR we register directly.
    // Ideally setup should be fast. Registering is "cleanest".

    // But since we deleted the user, we KNOW we must register.
    // So let's skip the "try login" step and go straight to register?
    // Or we keep the robust flow. Robust flow is safer if delete fails.

    await page.goto('/login');

    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');

    try {
        await expect(page).toHaveURL('/dashboard', { timeout: 5000 });
    } catch (e) {
        // Login failed, likely user does not exist. Let's Register.
        console.log('Login failed, attempting registration...');
        await page.goto('/register');
        await page.fill('input[name="username"]', username);
        await page.fill('input[name="email"]', email);
        await page.fill('input[name="password"]', password);
        await page.fill('input[name="confirmPassword"]', password);

        // Agree to terms
        await page.locator('input[type="checkbox"]').check();

        await page.click('button[type="submit"]');

        // After registration, we should be redirected to verify-email
        await page.waitForURL('**/verify-email**');

        console.log('Registration complete. Verifying email and role...');
        // Use DB helper to verify email
        verifyUserEmail(email);

        // Let's try to login again
        await page.goto('/login');
        await page.fill('input[name="email"]', email);
        await page.fill('input[name="password"]', password);
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/dashboard');
    }

    // Save auth state
    await page.context().storageState({ path: authFile });
});
