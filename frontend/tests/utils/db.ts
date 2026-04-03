import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);

const escapeSqlLiteral = (value: string) => value.replace(/'/g, "''");

const executeDbCommand = (sql: string, description: string) => {
    try {
        console.log(`${description}...`);
        const __dirname = path.dirname(__filename);
        const rootEnvFile = path.resolve(__dirname, '../../../.env');
        const defaultComposePath = path.resolve(__dirname, '../../../backend/docker-compose.ci.yml');
        const composeFile = process.env.CI_COMPOSE_FILE || defaultComposePath;
        const envFile = process.env.CI_ENV_FILE || rootEnvFile;
        const command = `docker compose --env-file "${envFile}" -f "${composeFile}" exec -T db psql -U postgres -d gameai -c "${sql}"`;
        execSync(command, { stdio: 'inherit' });
        console.log(`Success: ${description}.`);
    } catch (error) {
        console.error(`Failed: ${description}:`, error);
        throw error;
    }
};

export const promoteUserToAdmin = (email: string) => {
    const safeEmail = escapeSqlLiteral(email);

    executeDbCommand(
        `UPDATE users SET role = 'ADMIN' WHERE email = '${safeEmail}';`,
        `Promoting user ${email} to admin`
    );
};

export const verifyUserEmail = (email: string) => {
    const safeEmail = escapeSqlLiteral(email);

    executeDbCommand(
        `UPDATE users SET email_verified = true WHERE email = '${safeEmail}';`,
        `Verifying email for user ${email}`
    );
};

export const setEmailVerificationToken = (email: string, token: string) => {
    // Compute SHA256 hash of the token
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    const safeEmail = escapeSqlLiteral(email);

    executeDbCommand(
        `UPDATE users SET email_verification_token_hash = '${tokenHash}', email_verification_expires_at = NOW() + interval '24 hours' WHERE email = '${safeEmail}';`,
        `Setting verification token for user ${email}`
    );
};

export const deleteUserByEmail = (email: string) => {
    const safeEmail = escapeSqlLiteral(email);

    executeDbCommand(
        `
        DELETE FROM build_jobs
        WHERE submission_id IN (
            SELECT id FROM submissions
            WHERE user_id IN (
                SELECT id FROM users WHERE email = '${safeEmail}'
            )
        );

        DELETE FROM agents
        WHERE user_id IN (
            SELECT id FROM users WHERE email = '${safeEmail}'
        );

        DELETE FROM submissions
        WHERE user_id IN (
            SELECT id FROM users WHERE email = '${safeEmail}'
        );

        DELETE FROM users WHERE email = '${safeEmail}';
        `,
        `Deleting user ${email} and owned test data`
    );
};

export const createUnverifiedUser = (username: string, email: string) => {
    // Generate a new UUID for the user
    const id = crypto.randomUUID();
    // Use a dummy hash for password since we won't log in
    const dummyHash = 'dummy_hash_for_test';
    const safeUsername = escapeSqlLiteral(username);
    const safeEmail = escapeSqlLiteral(email);

    executeDbCommand(
        `INSERT INTO users (id, username, email, password_hash, role, email_verified, created_at, updated_at) VALUES ('${id}', '${safeUsername}', '${safeEmail}', '${dummyHash}', 'GUEST', false, NOW(), NOW());`,
        `Creating unverified user ${username} (${email})`
    );
    return id;
};

export const setSubmissionBuildStatus = (
    submissionId: string,
    status: 'queued' | 'running' | 'completed' | 'failed',
    options?: {
        logs?: string;
        imageId?: string;
        imageTag?: string;
    }
) => {
    const safeSubmissionId = escapeSqlLiteral(submissionId);
    const dbStatus = status.toUpperCase();
    const safeLogs = escapeSqlLiteral(options?.logs ?? `Test forced build status: ${status}`);
    const imageId = options?.imageId ?? (status === 'completed' ? `sha256:${submissionId}` : '');
    const imageTag = options?.imageTag ?? (status === 'completed' ? `agent:${submissionId}` : '');
    const safeImageId = escapeSqlLiteral(imageId);
    const safeImageTag = escapeSqlLiteral(imageTag);

    executeDbCommand(
        `
        UPDATE build_jobs
        SET
            status = '${dbStatus}',
            logs = '${safeLogs}',
            image_id = ${status === 'completed' ? `'${safeImageId}'` : 'NULL'},
            image_tag = ${status === 'completed' ? `'${safeImageTag}'` : 'NULL'},
            updated_at = NOW()
        WHERE submission_id = '${safeSubmissionId}';
        `,
        `Setting build status for submission ${submissionId} to ${status}`
    );
};
