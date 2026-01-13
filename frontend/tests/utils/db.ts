import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);

const executeDbCommand = (sql: string, description: string) => {
    try {
        console.log(`${description}...`);
        const composeFile = process.env.CI_COMPOSE_FILE || '../backend/docker-compose.yml';
        const command = `docker compose -f ${composeFile} exec -T db psql -U postgres -d gameai -c "${sql}"`;
        execSync(command, { stdio: 'inherit' });
        console.log(`Success: ${description}.`);
    } catch (error) {
        console.error(`Failed: ${description}:`, error);
        throw error;
    }
};

export const promoteUserToAdmin = (email: string) => {
    executeDbCommand(
        `UPDATE users SET role = 'ADMIN' WHERE email = '${email}';`,
        `Promoting user ${email} to admin`
    );
};

export const verifyUserEmail = (email: string) => {
    executeDbCommand(
        `UPDATE users SET email_verified = true WHERE email = '${email}';`,
        `Verifying email for user ${email}`
    );
};

export const setEmailVerificationToken = (email: string, token: string) => {
    // Compute SHA256 hash of the token
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

    executeDbCommand(
        `UPDATE users SET email_verification_token_hash = '${tokenHash}', email_verification_expires_at = NOW() + interval '24 hours' WHERE email = '${email}';`,
        `Setting verification token for user ${email}`
    );
};

export const deleteUserByEmail = (email: string) => {
    executeDbCommand(
        `DELETE FROM users WHERE email = '${email}';`,
        `Deleting user ${email}`
    );
};

export const createUnverifiedUser = (username: string, email: string) => {
    // Generate a new UUID for the user
    const id = crypto.randomUUID();
    // Use a dummy hash for password since we won't log in
    const dummyHash = 'dummy_hash_for_test';

    executeDbCommand(
        `INSERT INTO users (id, username, email, password_hash, role, email_verified, created_at, updated_at) VALUES ('${id}', '${username}', '${email}', '${dummyHash}', 'GUEST', false, NOW(), NOW());`,
        `Creating unverified user ${username} (${email})`
    );
    return id;
};
