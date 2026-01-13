import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.join(__dirname, '../.auth');

export const TEST_USERS = {
    standard: {
        username: 'testuser_e2e',
        email: 'test-e2e@example.com',
        password: 'ComplexPass!2024!Secure',
        authFile: path.join(AUTH_DIR, 'user.json'),
    },
    admin: {
        username: 'testuser_admin',
        email: 'test-admin@example.com',
        password: 'ComplexPass!2024!Secure',
        authFile: path.join(AUTH_DIR, 'admin.json'),
    },
};
