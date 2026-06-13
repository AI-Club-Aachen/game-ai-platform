import { apiRequest } from './client';

/**
 * Tournaments API — double-elimination tournaments between agents.
 * Mirrors backend/app/schemas/tournament.py.
 */

export type TournamentStatus = 'pending' | 'running' | 'completed' | 'cancelled' | 'needs_attention';
export type BracketSide = 'winners' | 'losers' | 'grand_final' | 'grand_final_reset';
export type MatchupStatus = 'pending' | 'in_progress' | 'completed' | 'needs_attention' | 'cancelled';
export type GameResolution = 'played' | 'draw_coin_flip' | 'forfeit_client_error' | 'admin_resolved';

export interface TournamentConfig {
    turn_time_limit: number;
    max_concurrent_matches: number;
    state_init_data: Record<string, unknown>;
}

export interface Tournament {
    id: string;
    name: string;
    game_type: string;
    status: TournamentStatus;
    config: TournamentConfig;
    winner_agent_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface TournamentGame {
    id: string;
    game_index: number;
    match_id: string | null;
    retry_count: number;
    winner_agent_id: string | null;
    resolution: GameResolution | null;
}

export type SlotSourceRole = 'winner' | 'loser';

export interface TournamentMatchup {
    id: string;
    bracket: BracketSide;
    round: number;
    position: number;
    stage: number;
    agent1_id: string | null;
    agent2_id: string | null;
    slot1_source_matchup_id: string | null;
    slot1_source_role: SlotSourceRole | null;
    slot2_source_matchup_id: string | null;
    slot2_source_role: SlotSourceRole | null;
    status: MatchupStatus;
    winner_agent_id: string | null;
    games: TournamentGame[];
    created_at: string;
    updated_at: string;
}

export interface TournamentEntrant {
    agent_id: string;
    seed: number | null;
    agent_name: string | null;
}

export interface TournamentStanding {
    agent_id: string;
    agent_name: string | null;
    seed: number | null;
    placement: number | null;
    matchup_wins: number;
    matchup_losses: number;
    eliminated_in_bracket: BracketSide | null;
    eliminated_in_round: number | null;
}

export interface TournamentBracket {
    tournament: Tournament;
    entrants: TournamentEntrant[];
    matchups: TournamentMatchup[];
    standings: TournamentStanding[];
}

export interface TournamentCreateRequest {
    name: string;
    game_type: string;
    agent_ids: string[];
    config?: Partial<TournamentConfig>;
}

export const tournamentsApi = {
    /**
     * List tournaments (optionally filtered by game type / status).
     */
    getTournaments: async (params?: {
        game_type?: string;
        status?: TournamentStatus;
        skip?: number;
        limit?: number;
    }) => {
        const queryParams = new URLSearchParams();
        if (params?.game_type) queryParams.append('game_type', params.game_type);
        if (params?.status) queryParams.append('status', params.status);
        if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
        if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/tournaments?${queryString}` : '/tournaments';

        return apiRequest<Tournament[]>(endpoint, { method: 'GET' });
    },

    /**
     * Get a tournament by ID.
     */
    getTournament: async (tournamentId: string) => {
        return apiRequest<Tournament>(`/tournaments/${tournamentId}`, { method: 'GET' });
    },

    /**
     * Get the full bracket (entrants, matchups with games, standings).
     */
    getBracket: async (tournamentId: string) => {
        return apiRequest<TournamentBracket>(`/tournaments/${tournamentId}/bracket`, { method: 'GET' });
    },

    /**
     * Create a tournament with an explicit set of entrant agents. Admin only.
     */
    createTournament: async (data: TournamentCreateRequest) => {
        return apiRequest<Tournament>('/tournaments', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Seed the bracket and queue round 1. Admin only.
     */
    startTournament: async (tournamentId: string) => {
        return apiRequest<Tournament>(`/tournaments/${tournamentId}/start`, { method: 'POST' });
    },

    /**
     * Cancel a tournament. Admin only.
     */
    cancelTournament: async (tournamentId: string) => {
        return apiRequest<Tournament>(`/tournaments/${tournamentId}/cancel`, { method: 'POST' });
    },

    /**
     * Resolve a stuck (needs_attention) matchup by declaring a winner. Admin only.
     */
    resolveMatchup: async (tournamentId: string, matchupId: string, winnerAgentId: string) => {
        return apiRequest<TournamentMatchup>(`/tournaments/${tournamentId}/matchups/${matchupId}/resolve`, {
            method: 'POST',
            body: JSON.stringify({ winner_agent_id: winnerAgentId }),
        });
    },
};
