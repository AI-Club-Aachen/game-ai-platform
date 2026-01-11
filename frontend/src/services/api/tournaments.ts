import { apiRequest } from './client';

/**
 * Tournaments API
 */
export const tournamentsApi = {
    /**
     * Get all tournaments
     */
    getTournaments: async () => {
        return apiRequest<Array<{
            id: string;
            name: string;
            game_id: string;
            status: string;
            start_date: string;
            end_date: string;
        }>>('/tournaments', {
            method: 'GET',
        });
    },

    /**
     * Get a specific tournament by ID
     */
    getTournament: async (tournamentId: string) => {
        return apiRequest<{
            id: string;
            name: string;
            game_id: string;
            status: string;
            start_date: string;
            end_date: string;
            participants?: Array<{
                user_id: string;
                username: string;
            }>;
        }>(`/tournaments/${tournamentId}`, {
            method: 'GET',
        });
    },

    /**
     * Register for a tournament
     */
    registerForTournament: async (tournamentId: string, submissionId: string) => {
        return apiRequest<{
            message: string;
        }>(`/tournaments/${tournamentId}/register`, {
            method: 'POST',
            body: JSON.stringify({ submission_id: submissionId }),
        });
    },
};
