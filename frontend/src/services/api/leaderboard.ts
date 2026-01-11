import { apiRequest } from './client';

/**
 * Leaderboard API
 */
export const leaderboardApi = {
    /**
     * Get leaderboard for a specific game
     */
    getLeaderboard: async (gameId: string) => {
        return apiRequest<Array<{
            rank: number;
            user_id: string;
            username: string;
            score: number;
            wins: number;
            losses: number;
            draws: number;
            total_matches: number;
        }>>(`/leaderboard/${gameId}`, {
            method: 'GET',
        });
    },
};
