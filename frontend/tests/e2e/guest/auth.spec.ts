import { test, expect } from '@playwright/test';
import { verifyUserEmail, setEmailVerificationToken } from '../../utils/db';

test.describe('Authentication', () => {

    // This test file uses the default 'chromium' project which has the storage state loaded.
    // So 'test' here is ALREADY authenticated as the setup user.
    // If we want to test LOGIN flow specifically, we should use a clean context or browser.

    test.use({ storageState: { cookies: [], origins: [] } }); // Start with clean state for login tests

    test('should display password requirements checklist on register page', async ({ page }) => {
        await page.goto('/register');

        // Type a weak password to trigger validations
        await page.fill('input[name="password"]', 'weak');

        // Check if validations appear (Red X icons)
        // We look for specific text and verifying the icon/color state might be complex via CSS selectors alone,
        // but we can check if the list items are present.
        // Based on implementation, met requirements have CheckCircle (success.main), unmet have Cancel (error.main).
        // Let's verify the text exists first.
        await expect(page.getByText('At least 12 characters')).toBeVisible();
        await expect(page.getByText('One uppercase letter (A-Z)')).toBeVisible();

        // Type a valid password
        await page.fill('input[name="password"]', 'StrongPass123!');

        // You might want to assert that the "success" icons are visible now, 
        // or just rely on the fact that form submission is allowed (covered in happy path test).
        // For visual tests, we mainly ensure the checklist is present.
    });

    test('should toggle password visibility on register page', async ({ page }) => {
        await page.goto('/register');

        const passwordInput = page.locator('input[name="password"]');
        const confirmInput = page.locator('input[name="confirmPassword"]');

        // Fill inputs first
        await passwordInput.fill('Secret123!');
        await confirmInput.fill('Secret123!');

        // Initial state should be type="password"
        await expect(passwordInput).toHaveAttribute('type', 'password');
        await expect(confirmInput).toHaveAttribute('type', 'password');

        // Click eye icon for password (assuming it's the first button in the input adornment)
        // We use aria-label to be specific since we added it
        await page.locator('button[aria-label="toggle password visibility"]').click();
        await expect(passwordInput).toHaveAttribute('type', 'text');

        // Click again to hide
        await page.locator('button[aria-label="toggle password visibility"]').click();
        await expect(passwordInput).toHaveAttribute('type', 'password');

        // Toggle confirm password
        await page.locator('button[aria-label="toggle confirm password visibility"]').click();
        await expect(confirmInput).toHaveAttribute('type', 'text');
    });

    test('should toggle password visibility on login page', async ({ page }) => {
        await page.goto('/login');

        const passwordInput = page.locator('input[name="password"]');

        // Fill input first
        await passwordInput.fill('Secret123!');

        // Initial state
        await expect(passwordInput).toHaveAttribute('type', 'password');

        // Click eye icon
        await page.locator('button[aria-label="toggle password visibility"]').click();

        // Should be text now
        await expect(passwordInput).toHaveAttribute('type', 'text');

        // Hide again
        await page.locator('button[aria-label="toggle password visibility"]').click();
        await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('should allow user to login', async ({ page }) => {
        // Use a dynamic user for this test to avoid conflicts with global setup
        const uniqueSuffix = Date.now().toString();
        const testUser = {
            username: `guest_auth_${uniqueSuffix}`,
            email: `guest.auth.${uniqueSuffix}@example.com`,
            password: 'ComplexPass!2024!Secure'
        };

        // 1. Registration
        await page.goto('/register');
        await page.fill('input[name="username"]', testUser.username);
        await page.fill('input[name="email"]', testUser.email);
        await page.fill('input[name="password"]', testUser.password);
        await page.fill('input[name="confirmPassword"]', testUser.password);
        await page.locator('input[type="checkbox"]').check();
        await page.click('button[type="submit"]');

        // Wait for verify page
        await page.waitForURL('**/verify-email**');

        // 2. Verify Email (Backend override)
        // Use the token helper or direct DB verification
        const verificationToken = '1234567890123456'; // Must be >= 16 chars
        setEmailVerificationToken(testUser.email, verificationToken);

        // Visit verification link
        await page.goto(`/verify-email?token=${verificationToken}`);

        // Should be redirected to login or show success (adjust based on app flow)
        // Assuming it stays on verify-email with success message or redirects
        await expect(page.getByText('Your email has been successfully verified')).toBeVisible({ timeout: 15000 });

        // 3. Login
        await page.goto('/login');
        await page.fill('input[name="email"]', testUser.email);
        await page.fill('input[name="password"]', testUser.password);
        await page.click('button[type="submit"]');

        // 4. Verify Dashboard
        await expect(page).toHaveURL('/dashboard');

        // Cleanup
        // deleteUserByEmail(testUser.email); // Optional: if we want to clean up immediately
    });
});


