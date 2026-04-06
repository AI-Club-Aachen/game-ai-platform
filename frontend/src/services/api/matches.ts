import { apiRequest, API_BASE_URL } from './client';

/**
 * Matches API
 */
export const matchesApi = {
    /**
     * Get all matches
     */
    getMatches: async (params?: { game_type?: string; status?: string; skip?: number; limit?: number }) => {
        const queryParams = new URLSearchParams();
        if (params?.game_type) queryParams.append('game_type', params.game_type);
        if (params?.status) queryParams.append('status', params.status);
        if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
        if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/matches?${queryString}` : '/matches';

        return apiRequest<Array<{
            id: string;
            game_type: string;
            status: string;
            created_at: string;
            agent_ids: string[];
            result?: any;
            game_state?: any;
            updated_at: string;
            config: any;
        }>>(endpoint, {
            method: 'GET',
        });
    },

    /**
     * Get a specific match by ID
     */
    getMatch: async (matchId: string) => {
        return apiRequest<{
            id: string;
            game_type: string;
            status: string;
            created_at: string;
            agent_ids: string[];
            result?: any;
            game_state?: any;
            updated_at: string;
            config: any;
            players?: Array<{
                user_id: string;
                username: string;
                submission_id: string;
            }>;
        }>(`/matches/${matchId}`, {
            method: 'GET',
        });
    },

    /**
     * Create a new match
     */
    createMatch: async (matchData: {
        game_type: string;
        config: any;
        agent_ids: string[];
    }) => {
        return apiRequest<{
            id: string;
            game_type: string;
            status: string;
            created_at: string;
            agent_ids: string[];
            result?: any;
            game_state?: any;
            updated_at: string;
            config: any;
        }>('/matches', {
            method: 'POST',
            body: JSON.stringify(matchData),
        });
    },

    /**
     * Get the SSE stream URL for spectating a match
     */
    getMatchStreamUrl: (matchId: string): string => {
        return `${API_BASE_URL}/matches/${matchId}/stream`;
    },
};
