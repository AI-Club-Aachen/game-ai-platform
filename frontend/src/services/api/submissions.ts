import { apiRequest } from './client';

/**
 * Submissions API
 */
export const submissionsApi = {
    /**
     * Get all submissions for the current user
     */
    getSubmissions: async () => {
        return apiRequest<Array<{
            id: string;
            game_id: string;
            user_id: string;
            code: string;
            status: string;
            created_at: string;
        }>>('/submissions', {
            method: 'GET',
        });
    },

    /**
     * Submit agent code for a game
     */
    submitAgent: async (submissionData: {
        game_id: string;
        code: string;
        language?: string;
    }) => {
        return apiRequest<{
            submission_id: string;
            message: string;
        }>('/submissions', {
            method: 'POST',
            body: JSON.stringify(submissionData),
        });
    },

    /**
     * Get a specific submission by ID
     */
    getSubmission: async (submissionId: string) => {
        return apiRequest<{
            id: string;
            game_id: string;
            user_id: string;
            code: string;
            status: string;
            created_at: string;
        }>(`/submissions/${submissionId}`, {
            method: 'GET',
        });
    },
};
