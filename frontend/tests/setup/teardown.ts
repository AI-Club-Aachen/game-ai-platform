import { test as teardown } from '@playwright/test';
import { deleteUserByEmail } from '../utils/db';

teardown('cleanup test users', async () => {
    console.log('Global Teardown: Cleaning up test users...');
    try {
        deleteUserByEmail('test-e2e@example.com');
        deleteUserByEmail('test-admin@example.com');
        console.log('Cleanup successful.');
    } catch (error) {
        console.error('Global teardown failed:', error);
    }
});
