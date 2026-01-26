import { apiRequest } from './client';

/**
 * Games API
 */
export const gamesApi = {
    /**
     * Get all available games
     */
    getGames: async () => {
        return apiRequest<Array<{
            id: string;
            name: string;
            description: string;
            rules: string;
            max_players: number;
        }>>('/games', {
            method: 'GET',
        });
    },

    /**
     * Get a specific game by ID
     */
    getGame: async (gameId: string) => {
        return apiRequest<{
            id: string;
            name: string;
            description: string;
            rules: string;
            max_players: number;
        }>(`/games/${gameId}`, {
            method: 'GET',
        });
    },
};
