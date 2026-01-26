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

    test('should display password requirements on profile page', async ({ page }) => {
        await page.goto('/profile');

        // Type in new password field to show requirements
        await page.getByLabel(/^New Password$/).fill('weak');

        await expect(page.getByText('At least 12 characters')).toBeVisible();
        await expect(page.getByText('One uppercase letter (A-Z)')).toBeVisible();
    });

    test('should toggle password visibility on profile page', async ({ page }) => {
        await page.goto('/profile');

        const currentPassInput = page.getByLabel(/^Current Password$/);
        const newPassInput = page.getByLabel(/^New Password$/);
        const confirmPassInput = page.getByLabel(/^Confirm New Password$/); // Exact match to avoid confusion

        // Fill inputs first
        await currentPassInput.fill('OldSecret123!');
        await newPassInput.fill('NewSecret123!');
        await confirmPassInput.fill('NewSecret123!');

        // Initial state
        await expect(currentPassInput).toHaveAttribute('type', 'password');
        await expect(newPassInput).toHaveAttribute('type', 'password');
        await expect(confirmPassInput).toHaveAttribute('type', 'password');

        // Toggle Current Password
        await page.locator('button[aria-label="toggle current password visibility"]').click();
        await expect(currentPassInput).toHaveAttribute('type', 'text');

        // Toggle New Password
        await page.locator('button[aria-label="toggle new password visibility"]').click();
        await expect(newPassInput).toHaveAttribute('type', 'text');

        // Toggle Confirm Password
        await page.locator('button[aria-label="toggle confirm password visibility"]').click();
        await expect(confirmPassInput).toHaveAttribute('type', 'text');
    });

    test('should have consistent input field widths on profile', async ({ page }) => {
        await page.goto('/profile');

        const currentPassBox = await page.getByLabel(/^Current Password$/).boundingBox();
        const newPassBox = await page.getByLabel(/^New Password$/).boundingBox();
        const confirmPassBox = await page.getByLabel(/^Confirm New Password$/).boundingBox();

        expect(currentPassBox).toBeTruthy();
        expect(newPassBox).toBeTruthy();
        expect(confirmPassBox).toBeTruthy();

        if (currentPassBox && newPassBox && confirmPassBox) {
            // Allow small pixel difference due to padding/borders
            expect(Math.abs(currentPassBox.width - newPassBox.width)).toBeLessThan(5);
            expect(Math.abs(newPassBox.width - confirmPassBox.width)).toBeLessThan(5);
        }

        // Also check Username and Email alignment
        const usernameBox = await page.getByLabel('Username').boundingBox();
        const emailBox = await page.getByLabel('Email').boundingBox();

        expect(usernameBox).toBeTruthy();
        expect(emailBox).toBeTruthy();

        if (usernameBox && emailBox) {
            expect(Math.abs(usernameBox.width - emailBox.width)).toBeLessThan(5);
        }
    });
});
