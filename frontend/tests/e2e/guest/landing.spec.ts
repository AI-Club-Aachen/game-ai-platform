import { test, expect } from '@playwright/test';

test('landing page has title', async ({ page }) => {
    await page.goto('/');

    // Expect a title "to contain" a substring.
    // Adjust based on actual app title
    await expect(page).toHaveTitle(/Game AI Platform/);
});
