import { test, expect } from '@playwright/test';
import { TEST_USERS } from '../../utils/constants';

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
        await expect(page.getByRole('heading', { name: 'Profile' })).toBeVisible();

        // Verify user info is visible (using the setup user email)
        await expect(page.locator(`input[value="${TEST_USERS.standard.email}"]`)).toBeVisible();
    });

    test('should NOT be able to access admin users page', async ({ page }) => {
        // Standard user should not see admin page
        await page.goto('/users');
        // Standard user stays on /users but gets an error because API returns 403
        await expect(page.getByText('Failed to load users')).toBeVisible();
    });
});
