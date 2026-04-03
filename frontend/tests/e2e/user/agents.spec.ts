import path from 'path';

import { expect, test, type Locator, type Page } from '@playwright/test';
import { setSubmissionBuildStatus } from '../../utils/db';


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

async function extractIdFromLabel(page: Page): Promise<string> {
    const text = await page.getByText(/^ID:/).textContent();
    const match = text?.match(uuidRegex);
    expect(match?.[0]).toBeTruthy();
    return match![0];
}

async function createAgent(
    page: Page,
    options: {
        agentName?: string;
        gameId?: string;
    } = {},
): Promise<{ agentId: string }> {
    const gameId = options.gameId ?? 'tictactoe';
    await page.goto(`/agents/new?gameId=${gameId}`);
    await expect(page.getByRole('heading', { name: 'Create New Agent' })).toBeVisible();

    if (options.agentName) {
        await page.getByLabel('Agent Name').fill(options.agentName);
    }

    await page.getByRole('button', { name: 'Create Agent' }).click();
    await page.waitForURL(/\/agents\/[0-9a-f-]+$/i, { timeout: 15000 });

    return { agentId: await extractIdFromLabel(page) };
}

async function uploadSubmission(
    page: Page,
    options: {
        agentId?: string;
        submissionName?: string;
        uploadPath: string;
        finalStatus?: 'completed' | 'failed';
    },
): Promise<{ submissionId: string }> {
    const agentId = options.agentId;
    const submitButtonName = agentId ? 'Upload Submission' : 'Submit Agent';

    await page.goto(agentId ? `/submissions/new?agentId=${agentId}` : '/submissions/new');
    await expect(page.getByLabel('Submission Name')).toBeVisible();

    if (options.submissionName) {
        await page.getByLabel('Submission Name').fill(options.submissionName);
    }

    await page.locator('input[type="file"]').setInputFiles(options.uploadPath);
    const createSubmissionResponsePromise = page.waitForResponse((response) =>
        response.url().endsWith('/submissions') &&
        response.request().method() === 'POST' &&
        response.status() === 201
    );
    await page.getByRole('button', { name: submitButtonName }).click();

    const createSubmissionResponse = await createSubmissionResponsePromise;
    const submission = await createSubmissionResponse.json() as { id: string };
    const finalStatus = options.finalStatus ?? 'completed';

    setSubmissionBuildStatus(submission.id, finalStatus);

    if (!agentId || finalStatus === 'failed') {
        await page.waitForURL(new RegExp(`/submissions/${submission.id}$`), { timeout: 15000 });
        return { submissionId: submission.id };
    }

    await page.waitForURL(new RegExp(`/agents/${agentId}$`), { timeout: 15000 });
    return { submissionId: submission.id };
}

async function getSubmissionRow(page: Page, submissionName: string): Promise<Locator> {
    const row = page.getByRole('row').filter({ has: page.getByText(submissionName, { exact: true }) });
    await expect(row).toHaveCount(1);
    return row.first();
}

async function deleteViaConfirmation(
    page: Page,
    buttonName: string,
): Promise<void> {
    page.once('dialog', (dialog) => dialog.accept());
    await page.getByRole('button', { name: buttonName }).click();
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

        const { agentId } = await createAgent(page, { agentName });
        const { submissionId } = await uploadSubmission(page, {
            agentId,
            uploadPath: successUpload,
        });

        await page.goto(`/agents/${agentId}`);
        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();
        await expect(page.getByRole('button', { name: 'View Source Submission' })).toBeVisible();

        await page.getByRole('button', { name: 'View Source Submission' }).click();
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 10000 });

        await expect(page.getByRole('heading', { level: 4, name: submissionId })).toBeVisible();
    });

    test('should create a tic-tac-toe agent with both agent and submission names', async ({ page }) => {
        const agentName = uniqueName('ttt-agent');
        const submissionName = uniqueName('ttt-submission');

        const { agentId } = await createAgent(page, {
            agentName,
        });
        await uploadSubmission(page, {
            agentId,
            submissionName,
            uploadPath: successUpload,
        });

        await page.goto(`/agents/${agentId}`);
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

        await uploadSubmission(page, {
            agentId,
            submissionName: failedName,
            uploadPath: failUpload,
            finalStatus: 'failed',
        });

        await uploadSubmission(page, {
            agentId,
            submissionName: firstSuccessName,
            uploadPath: successUpload,
        });

        await uploadSubmission(page, {
            agentId,
            submissionName: secondSuccessName,
            uploadPath: successUpload,
        });

        await page.goto(`/agents/${agentId}`);
        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();

        const currentRow = await getSubmissionRow(page, secondSuccessName);
        await expect(currentRow.getByRole('button', { name: 'Use For Agent' })).toHaveCount(0);
        const otherSubmissionsDivider = page.getByText('Other Submissions');
        await expect(otherSubmissionsDivider).toBeVisible();
        await expect(currentRow).toBeVisible();

        const selectableRow = await getSubmissionRow(page, firstSuccessName);
        await expect(selectableRow.getByRole('button', { name: 'Use For Agent' })).toBeVisible();

        const failedRow = await getSubmissionRow(page, failedName);
        await expect(failedRow.getByText('failed', { exact: true })).toBeVisible();
        await expect(failedRow.getByRole('button', { name: 'Use For Agent' })).toHaveCount(0);
    });

    test('should show the shared submissions list across multiple agents', async ({ page }) => {
        const firstAgentName = uniqueName('shared-agent-one');
        const secondAgentName = uniqueName('shared-agent-two');
        const firstSubmissionName = uniqueName('shared-sub-one');
        const secondSubmissionName = uniqueName('shared-sub-two');

        const { agentId: firstAgentId } = await createAgent(page, { agentName: firstAgentName });
        const { agentId: secondAgentId } = await createAgent(page, { agentName: secondAgentName });

        await uploadSubmission(page, {
            agentId: firstAgentId,
            submissionName: firstSubmissionName,
            uploadPath: successUpload,
        });

        await uploadSubmission(page, {
            agentId: secondAgentId,
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

test.describe('Game Type Submission Isolation', () => {
    test.setTimeout(240000);

    test('chess agent should not show tictactoe submissions', async ({ page }) => {
        const chessAgentName = uniqueName('chess-agent');
        const tttAgentName = uniqueName('ttt-agent');
        const chessSubName = uniqueName('chess-sub');
        const tttSubName = uniqueName('ttt-sub');

        // Create chess agent + submission
        const { agentId: chessAgentId } = await createAgent(page, { agentName: chessAgentName, gameId: 'chess' });
        await uploadSubmission(page, { agentId: chessAgentId, submissionName: chessSubName, uploadPath: successUpload });

        // Create tictactoe agent + submission
        const { agentId: tttAgentId } = await createAgent(page, { agentName: tttAgentName, gameId: 'tictactoe' });
        await uploadSubmission(page, { agentId: tttAgentId, submissionName: tttSubName, uploadPath: successUpload });

        // Chess agent page should show its own submission only
        await page.goto(`/agents/${chessAgentId}`);
        await expect(page.getByRole('heading', { level: 4, name: chessAgentName })).toBeVisible();
        await expect(page.getByText(chessSubName, { exact: true })).toBeVisible();
        await expect(page.getByText(tttSubName, { exact: true })).toHaveCount(0);
    });
});

test.describe('User Agent Deletion Flows', () => {
    test.describe.configure({ mode: 'serial' });
    test.setTimeout(240000);

    test('should delete a submission and keep it deleted after refresh', async ({ page }) => {
        const submissionName = uniqueName('delete-submission');

        const { submissionId } = await uploadSubmission(page, {
            submissionName,
            uploadPath: successUpload,
        });

        await deleteViaConfirmation(page, 'Delete Submission');

        await page.goto('/games/tictactoe');
        await expect(page.getByRole('img').nth(2)).toBeHidden();
        await expect(page.getByText(submissionName, { exact: true })).toHaveCount(0);

        const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
        const apiRes = await page.request.get(`${backendUrl}/submissions/${submissionId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        expect(apiRes.status()).toBe(404);
    });

    test('should delete an agent and keep it deleted after refresh', async ({ page }) => {
        const agentName = uniqueName('delete-agent');
        const { agentId } = await createAgent(page, { agentName });

        await deleteViaConfirmation(page, 'Delete Agent');

        const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
        const apiRes = await page.request.get(`${backendUrl}/agents/${agentId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        expect(apiRes.status()).toBe(404);
    });

    test('should keep an agent but remove its connection when the linked submission is deleted', async ({ page }) => {
        const agentName = uniqueName('agent-kept');
        const submissionName = uniqueName('submission-deleted');

        const { agentId } = await createAgent(page, {
            agentName,
        });
        const { submissionId } = await uploadSubmission(page, {
            agentId,
            submissionName,
            uploadPath: successUpload,
        });

        await page.getByRole('button', { name: 'View Source Submission' }).click();
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 10000 });
        await deleteViaConfirmation(page, 'Delete Submission');

        await page.goto(`/agents/${agentId}`);
        await page.reload();
        await expect(page.getByRole('heading', { level: 4, name: agentName })).toBeVisible();
        await expect(page.getByRole('button', { name: 'View Source Submission' })).toHaveCount(0);
        await expect(page.getByText(submissionName, { exact: true })).toHaveCount(0);

        const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
        const apiRes = await page.request.get(`${backendUrl}/submissions/${submissionId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        expect(apiRes.status()).toBe(404);
    });

    test('should keep a submission but remove the connection when the linked agent is deleted', async ({ page }) => {
        const agentName = uniqueName('agent-deleted');
        const submissionName = uniqueName('submission-kept');

        const { agentId } = await createAgent(page, {
            agentName,
        });
        const { submissionId } = await uploadSubmission(page, {
            agentId,
            submissionName,
            uploadPath: successUpload,
        });

        await page.getByRole('button', { name: 'View Source Submission' }).click();
        await page.waitForURL(/\/submissions\/[0-9a-f-]+$/i, { timeout: 10000 });

        await page.goto(`/agents/${agentId}`);
        await deleteViaConfirmation(page, 'Delete Agent');

        const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
        const apiRes = await page.request.get(`${backendUrl}/agents/${agentId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        expect(apiRes.status()).toBe(404);

        await page.goto(`/submissions/${submissionId}`);
        await page.reload();
        await expect(page.getByRole('heading', { level: 4, name: submissionName })).toBeVisible();
        await expect(page.getByText(/^ID:/)).toBeVisible();
    });
});
