import path from 'path';
import { execFileSync } from 'child_process';

import { expect, test, type Page } from '@playwright/test';

import { countBuildJobsForSubmission, getLatestBuildJobForSubmission } from '../../utils/db';


const uploadsDir = path.resolve(process.cwd(), 'tests/utils/uploads');
const successUpload = path.join(uploadsDir, 'agent_success.zip');
const failUpload = path.join(uploadsDir, 'agent_fail.zip');
if (!process.env.BACKEND_URL) {
    throw new Error('BACKEND_URL is not defined');
}
const backendUrl = process.env.BACKEND_URL.replace(/\/$/, '');
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

async function createAgentWithSubmission(
    page: Page,
    agentName: string,
    submissionName: string,
): Promise<{ agentId: string; submissionId: string }> {
    await page.goto('/agents/new?gameId=tictactoe');
    await expect(page.getByRole('heading', { name: 'Create New Agent' })).toBeVisible();

    await page.getByLabel('Agent Name').fill(agentName);
    await page.getByLabel('Submission Name').fill(submissionName);
    await page.locator('input[type="file"]').setInputFiles(successUpload);
    await page.getByRole('button', { name: 'Create Agent' }).click();

    await page.waitForURL(/\/agents\/[0-9a-f-]+$/i, { timeout: 100000 });
    const agentId = await extractSubmissionId(page);

    await expect(page.locator('tr').filter({ hasText: submissionName }).getByRole('cell', { name: 'Completed', exact: true })).toBeVisible({
        timeout: 60000,
    });

    await page.getByRole('button', { name: 'View Source Submission' }).click();
    await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 10000 });
    const submissionId = await extractSubmissionId(page);

    return { agentId, submissionId };
}

function removeDockerImage(imageTag: string) {
    execFileSync('docker', ['image', 'rm', '-f', imageTag], {
        stdio: 'inherit',
        encoding: 'utf-8',
    });
}

test.describe('Real Build Pipeline', () => {
    test.describe.configure({ mode: 'serial' });
    test.setTimeout(90000);

    test('should complete a real submission build end-to-end', async ({ page }) => {
        const submissionName = uniqueName('real-build-success');

        const submissionId = await uploadSubmission(page, submissionName, successUpload);

        await expect(page.getByText('Build completed successfully! Your agent is ready to play.')).toBeVisible({
            timeout: 60000,
        });
        await expect(page.getByText('COMPLETED', { exact: true })).toBeVisible();
        await expect(page.getByText('Build success!')).toBeVisible();
        await expect(page.getByText(submissionId)).toBeVisible();
    });

    test('should surface a real failed submission build end-to-end', async ({ page }) => {
        const submissionName = uniqueName('real-build-failed');

        await uploadSubmission(page, submissionName, failUpload);

        await expect(page.getByText('FAILED', { exact: true })).toBeVisible({ timeout: 60000 });
        await expect(page.getByText(/Build failed:/)).toBeVisible();
    });

    test('should rebuild a completed submission if its Docker image is missing before a match', async ({ page, request, context }) => {
        test.setTimeout(180000);

        const page2 = await context.newPage();

        const [firstAgent, secondAgent] = await Promise.all([
            createAgentWithSubmission(
                page,
                uniqueName('missing-image-agent-one'),
                uniqueName('missing-image-sub-one'),
            ),
            createAgentWithSubmission(
                page2,
                uniqueName('missing-image-agent-two'),
                uniqueName('missing-image-sub-two'),
            ),
        ]);

        await page2.close();

        const firstBuildJob = getLatestBuildJobForSubmission(firstAgent.submissionId);
        expect(firstBuildJob.status).toBe('COMPLETED');
        expect(firstBuildJob.imageTag).toBeTruthy();

        removeDockerImage(firstBuildJob.imageTag!);

        const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
        const createMatchResponse = await request.post(`${backendUrl}/matches`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            data: {
                game_type: 'tictactoe',
                config: { turn_time_limit: 10 },
                agent_ids: [firstAgent.agentId, secondAgent.agentId],
            },
        });
        expect(createMatchResponse.status()).toBe(201);

        const match = await createMatchResponse.json() as { id: string };

        await expect.poll(() => countBuildJobsForSubmission(firstAgent.submissionId), {
            timeout: 45000,
            message: 'Expected match preparation to enqueue a replacement build for the missing agent image',
        }).toBeGreaterThan(1);

        await expect.poll(() => getLatestBuildJobForSubmission(firstAgent.submissionId).status, {
            timeout: 90000,
            message: 'Expected replacement build to complete before the match runs',
        }).toBe('COMPLETED');

        await expect.poll(async () => {
            const response = await request.get(`${backendUrl}/matches/${match.id}`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            const currentMatch = await response.json() as { status: string; result?: { reason?: string } | null };
            const status = currentMatch.status.toLowerCase();
            const reason = currentMatch.result?.reason ?? '';

            if (reason.includes('Image verification failed')) {
                return 'missing-image-failure';
            }

            return ['completed', 'failed', 'client_error'].includes(status) ? 'terminal-without-missing-image' : 'pending';
        }, {
            timeout: 90000,
            message: 'Expected match not to fail with a missing Docker image after rebuild',
        }).toBe('terminal-without-missing-image');
    });
});
