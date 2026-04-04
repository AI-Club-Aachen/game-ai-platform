import path from 'path';

import { expect, test, type Page } from '@playwright/test';


const uploadsDir = path.resolve(process.cwd(), 'tests/utils/uploads');
const successUpload = path.join(uploadsDir, 'agent_success.zip');
const failUpload = path.join(uploadsDir, 'agent_fail.zip');
const uuidRegex =
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

function uniqueName(prefix: string): string {
    return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

async function extractSubmissionId(page: Page): Promise<string> {
    const text = await page.getByText(/^ID:/).textContent();
    const match = text?.match(uuidRegex);
    expect(match?.[0]).toBeTruthy();
    return match![0];
}

async function uploadSubmission(page: Page, submissionName: string, uploadPath: string): Promise<string> {
    await page.goto('/submissions/new');
    await expect(page.getByRole('heading', { name: 'New Submission' })).toBeVisible();

    await page.getByLabel('Submission Name').fill(submissionName);
    await page.locator('input[type="file"]').setInputFiles(uploadPath);
    await page.getByRole('button', { name: 'Submit Agent' }).click();

    await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 30000 });
    return extractSubmissionId(page);
}

test.describe('Real Build Pipeline', () => {
    test.describe.configure({ mode: 'serial' });
    test.setTimeout(30000);

    test('should complete a real submission build end-to-end', async ({ page }) => {
        const submissionName = uniqueName('real-build-success');

        const submissionId = await uploadSubmission(page, submissionName, successUpload);

        await expect(page.getByText('Build completed successfully! Your agent is ready to play.')).toBeVisible({
            timeout: 24000,
        });
        await expect(page.getByText('COMPLETED', { exact: true })).toBeVisible();
        await expect(page.getByText('Build success!')).toBeVisible();
        await expect(page.getByText(submissionId)).toBeVisible();
    });

    test('should surface a real failed submission build end-to-end', async ({ page }) => {
        const submissionName = uniqueName('real-build-failed');

        await uploadSubmission(page, submissionName, failUpload);

        await expect(page.getByText('FAILED', { exact: true })).toBeVisible({ timeout: 24000 });
        await expect(page.getByText(/Build failed:/)).toBeVisible();
    });
});
