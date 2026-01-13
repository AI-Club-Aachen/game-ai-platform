import { test, expect } from '@playwright/test';

test.describe('Admin Features', () => {
    // We assume the test is authenticated as Admin via the 'admin' project in playwright.config.ts

    test('should be able to access admin user management', async ({ page }) => {
        await page.goto('/users');
        await expect(page).toHaveURL('/users');

        // Verify we see the user table
        await expect(page.locator('table')).toBeVisible();

        // Check if we see at least one user (ourselves)
        await expect(page.locator('td', { hasText: 'test-admin@example.com' })).toBeVisible();
    });
});
