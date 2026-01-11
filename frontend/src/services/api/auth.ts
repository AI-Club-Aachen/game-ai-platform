import { apiRequest } from './client';

/**
 * Authentication API
 */
export const authApi = {
    /**
     * Login with email and password
     */
    login: async (credentials: { email: string; password: string }) => {
        return apiRequest<{
            access_token: string;
            token_type: string;
            user_id: string;
            username: string;
            role: 'guest' | 'user' | 'admin';
        }>('/auth/login', {
            method: 'POST',
            body: JSON.stringify(credentials),
        });
    },

    /**
     * Register a new user
     */
    register: async (userData: {
        username: string;
        email: string;
        password: string;
    }) => {
        return apiRequest<{
            message: string;
            user_id: string;
        }>('/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    },

    /**
     * Logout (client-side only for now)
     */
    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_id');
    },
};
