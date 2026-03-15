import { apiRequest } from './client';

export interface BuildJob {
    id: string;
    submission_id: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    logs: string | null;
    image_id: string | null;
    image_tag: string | null;
    created_at: string;
    updated_at: string;
}

export interface Submission {
    id: string;
    user_id: string;
    agent_id: string;
    created_at: string;
    updated_at: string;
    build_jobs: BuildJob[];
}

/**
 * Submissions API
 */
export const submissionsApi = {
    /**
     * Get all submissions for the current user
     */
    getSubmissions: async (skip = 0, limit = 20) => {
        return apiRequest<Submission[]>(`/submissions?skip=${skip}&limit=${limit}`, {
            method: 'GET',
        });
    },

    /**
     * Submit agent zip file
     */
    submitAgent: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        return apiRequest<Submission>('/submissions', {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' },
        });
    },

    /**
     * Get a specific submission by ID
     */
    getSubmission: async (submissionId: string) => {
        return apiRequest<Submission>(`/submissions/${submissionId}`, {
            method: 'GET',
        });
    },
};
