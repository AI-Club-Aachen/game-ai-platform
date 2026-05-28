import { test, expect } from '@playwright/test';

test('landing page has title', async ({ page }) => {
    await page.goto('/');

    // Expect a title "to contain" a substring.
    // Adjust based on actual app title
    await expect(page).toHaveTitle(/Game AI Platform/);
});

test('landing page exposes legal links', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('link', { name: 'Imprint' })).toHaveAttribute('href', '/imprint');
    await expect(page.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy-policy');
    await expect(page.getByRole('link', { name: 'Cookie Settings' })).toHaveAttribute('href', '/cookie-settings');
    await expect(page.getByRole('link', { name: 'Terms of Use' })).toHaveAttribute('href', '/terms-of-use');
});

[
    { path: '/imprint', heading: 'Imprint' },
    { path: '/privacy-policy', heading: 'Privacy Policy' },
    { path: '/cookie-settings', heading: 'Cookie Settings' },
    { path: '/terms-of-use', heading: 'Terms of Use' },
].forEach(({ path, heading }) => {
    test(`${heading} page is public`, async ({ page }) => {
        await page.goto(path);

        await expect(page.getByRole('heading', { name: heading, level: 1 })).toBeVisible();
    });
});
