import { test as teardown } from '@playwright/test';
import { deleteUserByEmail } from '../utils/db';
import { TEST_USERS } from '../utils/constants';
import fs from 'fs';

teardown('cleanup test users', async () => {
    console.log('Global Teardown: Cleaning up test users and auth files...');
    try {
        // Delete Users
        for (const userType of Object.values(TEST_USERS)) {
            deleteUserByEmail(userType.email);

            // Delete Auth File
            if (fs.existsSync(userType.authFile)) {
                try {
                    fs.unlinkSync(userType.authFile);
                    console.log(`Deleted auth file: ${userType.authFile}`);
                } catch (e) {
                    console.error(`Failed to delete auth file ${userType.authFile}:`, e);
                }
            }
        }
        console.log('Cleanup successful.');
    } catch (error) {
        console.error('Global teardown failed:', error);
    }
});
