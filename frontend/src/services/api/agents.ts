import { apiRequest } from './client';

export interface Agent {
    id: string;
    user_id: string;
    name: string;
    game_type: string;
    arena_id: string;
    active_submission_id: string | null;
    wins: number;
    losses: number;
    draws: number;
    matches_played: number;
    elo: number | null;
    created_at: string;
    updated_at: string;
}

export const agentsApi = {
    /**
     * Get all agents for the current user
     */
    getAgents: async (skip = 0, limit = 100, all_users = false) => {
        return apiRequest<Agent[]>(`/agents?skip=${skip}&limit=${limit}&all_users=${all_users}`, {
            method: 'GET',
        });
    },

    /**
     * Fetch every agent by paging through the API.
     * Pages through all results since limit is capped at 100.
     */
    getAllAgents: async (all_users = false) => {
        const pageSize = 100;
        const all: Agent[] = [];
        for (let skip = 0; ; skip += pageSize) {
            const page = await agentsApi.getAgents(skip, pageSize, all_users);
            all.push(...page);
            if (page.length < pageSize) break;
        }
        return all;
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
    createAgent: async (data: { user_id: string; game_type: string; name: string; arena_id: string; password?: string | null; active_submission_id?: string | null }) => {
        return apiRequest<Agent>('/agents', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Update an agent
     */
    updateAgent: async (agentId: string, data: { name?: string | null; active_submission_id?: string | null; wins?: number; losses?: number; draws?: number; matches_played?: number; elo?: number | null }) => {
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

    /**
     * Get the leaderboard for a specific game type
     */
    getLeaderboard: async (gameType: string, limit = 100) => {
        return apiRequest<any[]>(`/agents/leaderboard/${gameType}?limit=${limit}`, {
            method: 'GET',
        });
    },

    /**
     * Get the leaderboard for a specific arena
     */
    getLeaderboardByArena: async (arenaId: string, limit = 100) => {
        return apiRequest<any[]>(`/agents/leaderboard/arena/${arenaId}?limit=${limit}`, {
            method: 'GET',
        });
    },
};
