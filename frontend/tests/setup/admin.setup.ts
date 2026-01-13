import { test as setup, expect } from '@playwright/test';
import { promoteUserToAdmin, verifyUserEmail, deleteUserByEmail } from '../utils/db';
import { TEST_USERS } from '../utils/constants';
import fs from 'fs';

setup('authenticate as admin', async ({ page }) => {
    const { authFile, email, password, username } = TEST_USERS.admin;

    // Check if we have a valid auth file
    console.log(`Checking auth file at: ${authFile}`);
    const exists = fs.existsSync(authFile);
    console.log(`Auth file exists: ${exists}`);

    if (exists) {
        try {
            const content = fs.readFileSync(authFile, 'utf-8');
            const json = JSON.parse(content);
            // Basic validity check - ensure not empty
            if (Object.keys(json).length > 0) {
                console.log('Auth file exists and is valid, skipping setup.');
                return;
            }
        } catch (e) {
            console.log('Auth file exists but is invalid, recreating...');
        }
    }

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
