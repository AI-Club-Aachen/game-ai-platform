import { test, expect, Page } from '@playwright/test';

import { createUnverifiedUser, deleteUserByEmail } from '../../utils/db';

test.describe('Admin User Management', () => {
    // We assume the test is authenticated as Admin via the 'admin' project in playwright.config.ts

    const selectRole = async (page: Page, role: string) => {
        await page.getByText('All Roles').click();
        await page.getByRole('option', { name: role }).click();
    };
    const selectStatus = async (page: Page, status: string, exact: boolean = false) => {
        await page.getByText('All Status').click();
        await page.getByRole('option', { name: status, exact: exact }).click();
    };

    test('should be able to manually verify a user', async ({ page }) => {

        const username = 'test_guest_manual_verify';
        const email = 'test-guest-manual-verify@example.com';

        let userId: string;

        try {
            // 1. Create unverified user
            userId = createUnverifiedUser(username, email);

            // 2. Go to /users
            await page.goto('/users');

            // 3. Set filters
            await selectRole(page, 'Guest');
            await selectStatus(page, 'Unverified');

            // 4. Check if user pops up
            const userRow = page.locator('tr', { hasText: email });
            await expect(userRow).toBeVisible();
            await expect(userRow).toContainText(username);

            // 5. Verify request
            const verifyResponsePromise = page.waitForResponse(resp =>
                resp.url().includes(`/users/${userId}/verify-email`) &&
                resp.status() === 200
            );

            await userRow.getByRole('button', { name: 'Verify manually' }).click();
            await verifyResponsePromise;

            // 6. Check verification status change
            await page.reload();

            // Filter again to find the user (now verified)
            await selectRole(page, 'Guest');
            await selectStatus(page, 'Verified', true);

            const updatedRow = page.locator('tr', { hasText: email });
            await expect(updatedRow).toBeVisible();
            await expect(updatedRow).toContainText('Verified');

        } finally {
            if (email) {
                deleteUserByEmail(email);
            }
        }
    });

    test('should be able to manually update user role', async ({ page }) => {
        const username = 'test_guest_role_update';
        const email = 'test-guest-role-update@example.com';

        let userId: string;

        try {
            // 1. Create unverified user (Role defaults to GUEST)
            userId = createUnverifiedUser(username, email);

            // 2. Go to /users
            await page.goto('/users');

            // 3. Set filters
            await selectRole(page, 'Guest');
            await selectStatus(page, 'Unverified');

            // 4. Check if user pops up
            const userRow = page.locator('tr', { hasText: email });
            await expect(userRow).toBeVisible();

            // 5. Click "edit" button
            await userRow.locator('button').filter({ has: page.getByTestId('EditIcon') }).click();

            // 6. Click "Role" dropdown in pop up and change role to User
            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible();

            await dialog.getByRole('combobox').click();
            // MUI Select options are rendered in a portal at the document root, not inside the dialog
            await page.getByRole('option', { name: 'User' }).click();

            // 7. Save request
            const roleUpdatePromise = page.waitForResponse(resp =>
                resp.url().includes(`/users/${userId}/role`) &&
                resp.request().method() === 'PATCH' &&
                resp.status() === 200
            );

            await dialog.getByRole('button', { name: 'Save Changes' }).click();
            await roleUpdatePromise;

            // 8. Reload
            await page.reload();

            // 9. Filter again and verify ui change
            await selectRole(page, 'User');
            await selectStatus(page, 'Unverified');

            const updatedRow = page.locator('tr', { hasText: email });
            await expect(updatedRow).toBeVisible();
            await expect(updatedRow).toContainText('User');

        } finally {
            if (email) {
                deleteUserByEmail(email);
            }
        }
    });
});
