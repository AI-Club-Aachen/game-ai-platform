import { test, expect } from '@playwright/test';

test.describe('File Upload Formatting', () => {
    test('should correctly format file sizes as Bytes, KB, and MB', async ({ page }) => {
        // Go to the new submission page where the FileUploadBox is present
        await page.goto('/submissions/new');

        const fileInput = page.locator('input[type="file"]');

        // Test 500 Bytes
        await fileInput.setInputFiles({
            name: 'small.zip',
            mimeType: 'application/zip',
            buffer: Buffer.alloc(500)
        });
        console.log("asdasdasd")
        await expect(page.getByText('500 Bytes')).toBeVisible();

        // Test 500 KB (500 * 1024 = 512000 bytes)
        await fileInput.setInputFiles({
            name: 'medium.zip',
            mimeType: 'application/zip',
            buffer: Buffer.alloc(512000)
        });
        await expect(page.getByText('500.00 KB')).toBeVisible();

        // Test 5 MB (5 * 1024 * 1024 = 5242880 bytes)
        await fileInput.setInputFiles({
            name: 'large.zip',
            mimeType: 'application/zip',
            buffer: Buffer.alloc(5242880)
        });
        await expect(page.getByText('5.00 MB')).toBeVisible();
    });
});
