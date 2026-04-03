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
    name: string;
    created_at: string;
    updated_at: string;
    build_jobs: BuildJob[];
}

export function getLatestBuildJob(submission: Submission): BuildJob | null {
    if (!submission.build_jobs.length) {
        return null;
    }

    return [...submission.build_jobs].sort((left, right) => {
        const leftTime = Date.parse(left.updated_at || left.created_at);
        const rightTime = Date.parse(right.updated_at || right.created_at);
        return rightTime - leftTime;
    })[0] ?? null;
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
    submitAgent: async (file: File, name?: string) => {
        const formData = new FormData();
        formData.append('file', file);
        if (name && name.trim()) {
            formData.append('name', name.trim());
        }

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

    deleteSubmission: async (submissionId: string) => {
        return apiRequest<void>(`/submissions/${submissionId}`, {
            method: 'DELETE',
        });
    },
};
