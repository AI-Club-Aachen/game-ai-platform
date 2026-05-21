import { test, expect, type Locator, type Page } from '@playwright/test';

const missingAgentEntryMessage =
    "No agent entry file found. Expected 'agent.py' or a file ending with '_agent.py' at the root of the ZIP file or inside a single top-level folder. Please check your ZIP file structure to ensure the agent file is not nested too deeply.";

const getDropZone = (page: Page, title: string) =>
    page
        .getByText(title)
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

const crc32Table = Array.from({ length: 256 }, (_, index) => {
    let crc = index;
    for (let bit = 0; bit < 8; bit += 1) {
        crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
    }
    return crc >>> 0;
});

const crc32 = (buffer: Buffer) => {
    let crc = 0xffffffff;
    for (const byte of buffer) {
        crc = crc32Table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
};

const createZipBuffer = (files: Record<string, string>) => {
    const localFileParts: Buffer[] = [];
    const centralDirectoryParts: Buffer[] = [];
    let offset = 0;

    Object.entries(files).forEach(([filename, content]) => {
        const name = Buffer.from(filename);
        const data = Buffer.from(content);
        const checksum = crc32(data);

        const localHeader = Buffer.alloc(30);
        localHeader.writeUInt32LE(0x04034b50, 0);
        localHeader.writeUInt16LE(20, 4);
        localHeader.writeUInt16LE(0, 6);
        localHeader.writeUInt16LE(0, 8);
        localHeader.writeUInt16LE(0, 10);
        localHeader.writeUInt16LE(0, 12);
        localHeader.writeUInt32LE(checksum, 14);
        localHeader.writeUInt32LE(data.length, 18);
        localHeader.writeUInt32LE(data.length, 22);
        localHeader.writeUInt16LE(name.length, 26);
        localHeader.writeUInt16LE(0, 28);

        localFileParts.push(localHeader, name, data);

        const centralHeader = Buffer.alloc(46);
        centralHeader.writeUInt32LE(0x02014b50, 0);
        centralHeader.writeUInt16LE(20, 4);
        centralHeader.writeUInt16LE(20, 6);
        centralHeader.writeUInt16LE(0, 8);
        centralHeader.writeUInt16LE(0, 10);
        centralHeader.writeUInt16LE(0, 12);
        centralHeader.writeUInt16LE(0, 14);
        centralHeader.writeUInt32LE(checksum, 16);
        centralHeader.writeUInt32LE(data.length, 20);
        centralHeader.writeUInt32LE(data.length, 24);
        centralHeader.writeUInt16LE(name.length, 28);
        centralHeader.writeUInt16LE(0, 30);
        centralHeader.writeUInt16LE(0, 32);
        centralHeader.writeUInt16LE(0, 34);
        centralHeader.writeUInt16LE(0, 36);
        centralHeader.writeUInt32LE(0, 38);
        centralHeader.writeUInt32LE(offset, 42);
        centralDirectoryParts.push(centralHeader, name);

        offset += localHeader.length + name.length + data.length;
    });

    const centralDirectory = Buffer.concat(centralDirectoryParts);
    const endOfCentralDirectory = Buffer.alloc(22);
    endOfCentralDirectory.writeUInt32LE(0x06054b50, 0);
    endOfCentralDirectory.writeUInt16LE(0, 4);
    endOfCentralDirectory.writeUInt16LE(0, 6);
    endOfCentralDirectory.writeUInt16LE(Object.keys(files).length, 8);
    endOfCentralDirectory.writeUInt16LE(Object.keys(files).length, 10);
    endOfCentralDirectory.writeUInt32LE(centralDirectory.length, 12);
    endOfCentralDirectory.writeUInt32LE(offset, 16);
    endOfCentralDirectory.writeUInt16LE(0, 20);

    return Buffer.concat([...localFileParts, centralDirectory, endOfCentralDirectory]);
};

const uniqueName = (prefix: string) =>
    `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;

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

    [
        {
            name: 'new submission',
            path: '/submissions/new',
            dropZoneTitle: 'Select a ZIP file to upload',
            submitButtonName: 'Submit Agent',
        },
        {
            name: 'new agent',
            path: '/agents/new',
            dropZoneTitle: 'Drag and drop a ZIP file here, or Browse Files',
            submitButtonName: 'Create Agent',
        },
    ].forEach(({ name, path, dropZoneTitle, submitButtonName }) => {
        test(`should highlight during drag and accept a dropped ZIP file on ${name}`, async ({ page }) => {
            await page.goto(path);

            const dropZone = getDropZone(page, dropZoneTitle);
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
            await expect(page.getByRole('button', { name: 'Change File' })).toBeVisible();
            await expect(page.getByRole('button', { name: submitButtonName })).toBeEnabled();

            await dragDataTransfer.dispose();
        });
    });

    test('should show the agent entry file structure error in build logs for a deeply nested ZIP', async ({ page }) => {
        test.setTimeout(60000);

        await page.goto('/submissions/new');
        await expect(page.getByRole('heading', { name: 'New Submission' })).toBeVisible();

        await page.getByLabel('Submission Name').fill(uniqueName('deeply-nested-agent'));
        await page.locator('input[type="file"]').setInputFiles({
            name: 'deeply-nested-agent.zip',
            mimeType: 'application/zip',
            buffer: createZipBuffer({
                'nested/too/deep/agent.py': "print('this agent is nested too deeply')\n",
            }),
        });

        await page.getByRole('button', { name: 'Submit Agent' }).click();
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 30000 });

        await expect(page.getByText('FAILED', { exact: true })).toBeVisible({ timeout: 30000 });
        await expect(page.getByText(missingAgentEntryMessage)).toBeVisible();
    });
});
