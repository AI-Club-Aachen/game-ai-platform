import { test, expect } from '@playwright/test';

test.describe('Protected Routes', () => {
    // Uses the global auth state from setup (Standard User)

    test('should be able to access dashboard', async ({ page }) => {
        await page.goto('/dashboard');
        await expect(page).toHaveURL('/dashboard');
        await expect(page.locator('text=Welcome')).toBeVisible();
    });

    test('should be able to access profile', async ({ page }) => {
        await page.goto('/profile');
        await expect(page).toHaveURL('/profile');
        await expect(page.locator('text=Profile')).toBeVisible();

        // Verify user info is visible (using the setup user email)
        await expect(page.locator('input[value="test-e2e@example.com"]')).toBeVisible();
    });

    test('should NOT be able to access admin users page', async ({ page }) => {
        // Standard user should not see admin page
        await page.goto('/users');
        // Expect to be redirected to dashboard or show unauthorized
        // Assuming redirection to /dashboard or staying on /users but showing error
        // If app redirects unauthorized users from /users to /dashboard:
        await expect(page).not.toHaveURL('/users');
    });
});
