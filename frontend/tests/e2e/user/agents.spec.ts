import path from 'path';

import { expect, test, type Locator, type Page } from '@playwright/test';


const uploadsDir = path.resolve(process.cwd(), 'tests/utils/uploads');
const successUpload = path.join(uploadsDir, 'agent_success.zip');
const failUpload = path.join(uploadsDir, 'agent_fail.zip');

const uuidRegex =
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

function uniqueName(prefix: string): string {
    return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

async function extractIdFromLabel(page: Page): Promise<string> {
    const text = await page.getByText(/^ID:/).textContent();
    const match = text?.match(uuidRegex);
    expect(match?.[0]).toBeTruthy();
    return match![0];
}

async function openTicTacToeCreateAgent(page: Page): Promise<void> {
    await page.goto('/agents/new?gameId=tictactoe');
    await expect(page.getByRole('heading', { name: 'Create New Agent' })).toBeVisible();
}

async function createAgent(
    page: Page,
    options: {
        agentName?: string;
        submissionName?: string;
        uploadPath?: string;
    } = {},
): Promise<{ agentId: string }> {
    await openTicTacToeCreateAgent(page);

    if (options.agentName) {
        await page.getByLabel('Agent Name').fill(options.agentName);
    }

    if (options.submissionName) {
        await page.getByLabel('Submission Name').fill(options.submissionName);
    }

    if (options.uploadPath) {
        await page.locator('input[type="file"]').setInputFiles(options.uploadPath);
    }

    await page.getByRole('button', { name: 'Create Agent' }).click();
    await page.waitForURL(/\/agents\/[0-9a-f-]+$/i, { timeout: 180000 });

    return { agentId: await extractIdFromLabel(page) };
}

async function uploadSubmissionFromAgentDetails(
    page: Page,
    agentId: string,
    options: {
        submissionName?: string;
        uploadPath: string;
        expectSuccess?: boolean;
    },
): Promise<void> {
    await page.goto(`/agents/${agentId}`);
    await page.getByRole('button', { name: 'Upload Submission' }).click();
    await page.waitForURL(new RegExp(`/submissions/new\\?agentId=${agentId}$`), { timeout: 10000 });

    if (options.submissionName) {
        await page.getByLabel('Submission Name').fill(options.submissionName);
    }

    await page.locator('input[type="file"]').setInputFiles(options.uploadPath);
    await page.getByRole('button', { name: 'Upload Submission' }).click();

    if (options.expectSuccess === false) {
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 180000 });
        return;
    }

    await page.waitForURL(new RegExp(`/agents/${agentId}$`), { timeout: 180000 });
}

async function getSubmissionRow(page: Page, submissionName: string): Promise<Locator> {
    const row = page.getByRole('row').filter({ has: page.getByText(submissionName, { exact: true }) });
    await expect(row).toHaveCount(1);
    return row.first();
}

test.describe('User Agent Flows', () => {
    test.describe.configure({ mode: 'serial' });
    test.setTimeout(240000);

    test('should create a tic-tac-toe agent without a name', async ({ page }) => {
        await createAgent(page);

        const agentId = await extractIdFromLabel(page);
        await expect(page.getByRole('heading', { level: 4, name: agentId })).toBeVisible();
        await expect(page.getByText('No submissions found for this agent')).toBeVisible();
    });

    test('should create a tic-tac-toe agent with a name', async ({ page }) => {
        const agentName = uniqueName('ttt-agent');

        await createAgent(page, { agentName });

        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();
        await expect(page.getByText(/^ID:/)).toBeVisible();
    });

    test('should create a tic-tac-toe agent with a named agent and an unnamed submission', async ({ page }) => {
        const agentName = uniqueName('ttt-agent');

        await createAgent(page, { agentName, uploadPath: successUpload });

        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();
        await expect(page.getByRole('button', { name: 'View Source Submission' })).toBeVisible();

        await page.getByRole('button', { name: 'View Source Submission' }).click();
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 10000 });

        const submissionId = await extractIdFromLabel(page);
        await expect(page.getByRole('heading', { level: 4, name: submissionId })).toBeVisible();
    });

    test('should create a tic-tac-toe agent with both agent and submission names', async ({ page }) => {
        const agentName = uniqueName('ttt-agent');
        const submissionName = uniqueName('ttt-submission');

        await createAgent(page, {
            agentName,
            submissionName,
            uploadPath: successUpload,
        });

        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();
        await expect(page.getByText(submissionName, { exact: true })).toBeVisible();

        await page.getByRole('button', { name: 'View Source Submission' }).click();
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 10000 });
        await expect(page.getByRole('heading', { level: 4, name: submissionName })).toBeVisible();
        await expect(page.getByText(/^ID:/)).toBeVisible();
    });

    test('should only allow switching to successful submissions that are not already selected', async ({ page }) => {
        const agentName = uniqueName('selection-agent');
        const firstSuccessName = uniqueName('success-one');
        const secondSuccessName = uniqueName('success-two');
        const failedName = uniqueName('failed-one');

        const { agentId } = await createAgent(page, { agentName });

        await uploadSubmissionFromAgentDetails(page, agentId, {
            submissionName: failedName,
            uploadPath: failUpload,
            expectSuccess: false,
        });

        await uploadSubmissionFromAgentDetails(page, agentId, {
            submissionName: firstSuccessName,
            uploadPath: successUpload,
        });

        await uploadSubmissionFromAgentDetails(page, agentId, {
            submissionName: secondSuccessName,
            uploadPath: successUpload,
        });

        await page.goto(`/agents/${agentId}`);
        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();

        const currentRow = await getSubmissionRow(page, secondSuccessName);
        await expect(currentRow).toContainText('Current');
        await expect(currentRow.getByRole('button', { name: 'Use For Agent' })).toHaveCount(0);

        const selectableRow = await getSubmissionRow(page, firstSuccessName);
        await expect(selectableRow.getByRole('button', { name: 'Use For Agent' })).toBeVisible();

        const failedRow = await getSubmissionRow(page, failedName);
        await expect(failedRow).toContainText('failed');
        await expect(failedRow.getByRole('button', { name: 'Use For Agent' })).toHaveCount(0);
    });

    test('should show the shared submissions list across multiple agents', async ({ page }) => {
        const firstAgentName = uniqueName('shared-agent-one');
        const secondAgentName = uniqueName('shared-agent-two');
        const firstSubmissionName = uniqueName('shared-sub-one');
        const secondSubmissionName = uniqueName('shared-sub-two');

        const { agentId: firstAgentId } = await createAgent(page, { agentName: firstAgentName });
        const { agentId: secondAgentId } = await createAgent(page, { agentName: secondAgentName });

        await uploadSubmissionFromAgentDetails(page, firstAgentId, {
            submissionName: firstSubmissionName,
            uploadPath: successUpload,
        });

        await uploadSubmissionFromAgentDetails(page, secondAgentId, {
            submissionName: secondSubmissionName,
            uploadPath: successUpload,
        });

        await page.goto(`/agents/${firstAgentId}`);
        await expect(page.getByText(firstSubmissionName, { exact: true })).toBeVisible();
        await expect(page.getByText(secondSubmissionName, { exact: true })).toBeVisible();

        await page.goto(`/agents/${secondAgentId}`);
        await expect(page.getByText(firstSubmissionName, { exact: true })).toBeVisible();
        await expect(page.getByText(secondSubmissionName, { exact: true })).toBeVisible();
    });
});
