import { apiRequest } from './client';

/**
 * Matches API
 */
export const matchesApi = {
    /**
     * Get all matches
     */
    getMatches: async (params?: { game_id?: string; user_id?: string }) => {
        const queryParams = new URLSearchParams();
        if (params?.game_id) queryParams.append('game_id', params.game_id);
        if (params?.user_id) queryParams.append('user_id', params.user_id);

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/matches?${queryString}` : '/matches';

        return apiRequest<Array<{
            id: string;
            game_id: string;
            status: string;
            created_at: string;
            completed_at?: string;
            result?: any;
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
            game_id: string;
            status: string;
            created_at: string;
            completed_at?: string;
            result?: any;
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
        game_id: string;
        player_submissions: string[];
    }) => {
        return apiRequest<{
            match_id: string;
            message: string;
        }>('/matches', {
            method: 'POST',
            body: JSON.stringify(matchData),
        });
    },
};
