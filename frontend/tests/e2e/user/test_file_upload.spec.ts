import { test, expect, type Locator, type Page } from '@playwright/test';

const getDropZone = (page: Page) =>
    page
        .getByText('Select a ZIP file to upload')
        .locator('xpath=ancestor::div[contains(@class, "MuiBox-root")][1]');

const getBackgroundColor = async (locator: Locator) =>
    locator.evaluate((element) => window.getComputedStyle(element).backgroundColor);

const createDragDataTransfer = async (
    page: Page,
    file: { name: string; mimeType: string; size: number }
) =>
    page.evaluateHandle(({ name, mimeType, size }) => {
        const dataTransfer = new DataTransfer();
        const bytes = new Uint8Array(size);
        const uploadedFile = new File([bytes], name, { type: mimeType });

        dataTransfer.items.add(uploadedFile);

        return dataTransfer;
    }, file);

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

    test('should highlight during drag and accept a dropped ZIP file', async ({ page }) => {
        await page.goto('/submissions/new');

        const dropZone = getDropZone(page);
        await expect(dropZone).toBeVisible();

        const defaultBackgroundColor = await getBackgroundColor(dropZone);
        const dragDataTransfer = await createDragDataTransfer(page, {
            name: 'dragged-agent.zip',
            mimeType: 'application/zip',
            size: 2048,
        });

        await dropZone.dispatchEvent('dragover', { dataTransfer: dragDataTransfer });
        await expect
            .poll(() => getBackgroundColor(dropZone))
            .not.toBe(defaultBackgroundColor);

        await dropZone.dispatchEvent('dragleave', { dataTransfer: dragDataTransfer });
        await expect
            .poll(() => getBackgroundColor(dropZone))
            .toBe(defaultBackgroundColor);

        await dropZone.dispatchEvent('dragover', { dataTransfer: dragDataTransfer });
        await dropZone.dispatchEvent('drop', { dataTransfer: dragDataTransfer });

        await expect(page.getByText('dragged-agent.zip')).toBeVisible();
        await expect(page.getByText('2.00 KB')).toBeVisible();
        await expect(page.getByRole('button', { name: 'Submit Agent' })).toBeEnabled();

        await dragDataTransfer.dispose();
    });
});
