import { apiRequest } from './client';

export interface Agent {
    id: string;
    user_id: string;
    name: string;
    game_type: string;
    active_submission_id: string | null;
    stats: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export const agentsApi = {
    /**
     * Get all agents for the current user
     */
    getAgents: async (skip = 0, limit = 500, all_users = false) => {
        return apiRequest<Agent[]>(`/agents?skip=${skip}&limit=${limit}&all_users=${all_users}`, {
            method: 'GET',
        });
    },

    /**
     * Get a specific agent by ID
     */
    getAgent: async (agentId: string) => {
        return apiRequest<Agent>(`/agents/${agentId}`, {
            method: 'GET',
        });
    },

    /**
     * Create a new agent
     */
    createAgent: async (data: { user_id: string; game_type: string; name?: string; active_submission_id?: string | null }) => {
        return apiRequest<Agent>('/agents', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Update an agent
     */
    updateAgent: async (agentId: string, data: { active_submission_id?: string | null; stats?: Record<string, any> }) => {
        return apiRequest<Agent>(`/agents/${agentId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    /**
     * Delete an agent
     */
    deleteAgent: async (agentId: string) => {
        return apiRequest<void>(`/agents/${agentId}`, {
            method: 'DELETE',
        });
    },
};
