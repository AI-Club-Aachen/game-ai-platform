import { apiRequest } from './client';

/**
 * Leaderboard API
 */
export const leaderboardApi = {
    /**
     * Get leaderboard for a specific game
     */
    getLeaderboard: async (gameId: string) => {
        const data = await apiRequest<any[]>(`/agents/leaderboard/${gameId}`, {
            method: 'GET',
        });

        return data.map((d: any, index: number) => ({
            rank: index + 1,
            user_id: d.id, // using agent id as unique key
            username: d.username,
            score: d.elo || 0,
            wins: d.wins,
            losses: d.losses,
            draws: d.draws,
            total_matches: d.matches_played || (d.wins + d.losses)
        }));
    },
};
