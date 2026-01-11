import { test as setup, expect } from '@playwright/test';
import { promoteUserToAdmin, verifyUserEmail, deleteUserByEmail } from '../utils/db';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const authFile = path.join(__dirname, '../playwright/.auth/admin.json');

setup('authenticate as admin', async ({ page }) => {
    const email = 'test-admin@example.com';
    const password = 'Test1!Test1!Test1';
    const username = 'testuser_admin';

    // Cleanup potential stale state
    try {
        console.log('Cleaning up old admin test user...');
        deleteUserByEmail(email);
    } catch (e) {
        console.log('Cleanup failed, continuing:', e);
    }

    // Register flow is most robust
    await page.goto('/register');
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.fill('input[name="confirmPassword"]', password);
    await page.locator('input[type="checkbox"]').check();
    await page.click('button[type="submit"]');

    // Wait for verify page
    await page.waitForURL('**/verify-email**');

    console.log('Admin registration complete. Promoting to Admin...');
    verifyUserEmail(email);
    promoteUserToAdmin(email);

    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');

    // Save auth state
    await page.context().storageState({ path: authFile });
});
