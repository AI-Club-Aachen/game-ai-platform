import { apiRequest, API_BASE_URL } from './client';

export interface HumanOpponent {
    id: string;
    agent_name: string;
    username: string;
    elo: number | null;
    is_mine: boolean;
}

export interface SchedulerConfig {
    enabled: boolean;
    interval_seconds: number;
    strategy: string;
    scheduling_strategy: string;
    /** Seconds a human player gets per move in human-vs-agent games */
    human_move_time_limit: number;
    /** Wall-clock cap (seconds) for a whole human-vs-agent game */
    human_match_max_duration: number;
}

/**
 * Matches API
 */
export const matchesApi = {
    /**
     * Get all matches
     */
    getMatches: async (params?: { game_type?: string; arena_id?: string; status?: string | string[]; skip?: number; limit?: number }) => {
        const queryParams = new URLSearchParams();
        if (params?.game_type) queryParams.append('game_type', params.game_type);
        if (params?.arena_id) queryParams.append('arena_id', params.arena_id);
        if (params?.status) {
            if (Array.isArray(params.status)) {
                params.status.forEach(s => queryParams.append('status', s));
            } else {
                queryParams.append('status', params.status);
            }
        }
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
        arena_id: string;
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
     * Start a game where the current user plays by hand against an agent.
     * human_player_index 0 = you move first, 1 = the agent moves first.
     */
    createHumanMatch: async (data: { arena_id: string; agent_id: string; human_player_index: number }) => {
        return apiRequest<{ id: string; status: string; agent_ids: string[] }>('/matches/human', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Agents of an arena the current user can play against by hand.
     */
    getHumanOpponents: async (arenaId: string) => {
        return apiRequest<HumanOpponent[]>(`/matches/human/opponents?arena_id=${encodeURIComponent(arenaId)}`, {
            method: 'GET',
        });
    },

    /**
     * Submit a move as the human player. `player` is filled in by the server.
     */
    submitHumanMove: async (matchId: string, move: Record<string, unknown>) => {
        return apiRequest<{ status: string }>(`/matches/${matchId}/human-move`, {
            method: 'POST',
            body: JSON.stringify({ move }),
        });
    },

    /**
     * Resign (or cancel, if still queued) your human-vs-agent game.
     */
    resignHumanMatch: async (matchId: string) => {
        return apiRequest<{ id: string; status: string }>(`/matches/${matchId}/resign`, {
            method: 'POST',
        });
    },

    /**
     * Get the SSE stream URL for spectating a match
     */
    getMatchStreamUrl: (matchId: string): string => {
        return `${API_BASE_URL}/matches/${matchId}/stream`;
    },

    /**
     * Get scheduler configuration
     */
    getSchedulerConfig: async () => {
        return apiRequest<SchedulerConfig>('/matches/scheduler/config', {
            method: 'GET',
        });
    },

    /**
     * Update scheduler configuration
     */
    updateSchedulerConfig: async (config: SchedulerConfig) => {
        return apiRequest<SchedulerConfig>('/matches/scheduler/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    },
};
