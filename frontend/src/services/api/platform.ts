import { apiRequest } from './client';

/**
 * Platform-wide admin controls.
 */

export interface SubmissionFreeze {
    enabled: boolean;
    updated_at: string;
    updated_by_user_id: string | null;
}

export const platformApi = {
    /**
     * Current submission-freeze state. Readable by any verified user.
     */
    getSubmissionFreeze: async () => {
        return apiRequest<SubmissionFreeze>('/platform/submission-freeze', { method: 'GET' });
    },

    /**
     * Enable or disable the submission freeze. Admin only.
     */
    setSubmissionFreeze: async (enabled: boolean) => {
        return apiRequest<SubmissionFreeze>('/platform/submission-freeze', {
            method: 'PUT',
            body: JSON.stringify({ enabled }),
        });
    },
};
