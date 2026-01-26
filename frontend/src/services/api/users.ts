import { apiRequest } from './client';

/**
 * Users API (Profile & Admin)
 */
export const usersApi = {
    /**
     * Get current user profile
     */
    getCurrentUser: async () => {
        return apiRequest<{
            id: string;
            username: string;
            email: string;
            role: 'guest' | 'user' | 'admin';
            is_verified: boolean;
            profile_picture_url?: string;
            created_at: string;
            updated_at: string;
        }>('/users/me', {
            method: 'GET',
        });
    },

    /**
     * Update user profile
     */
    updateProfile: async (data: { username?: string; email?: string }) => {
        return apiRequest<{
            id: string;
            username: string;
            email: string;
            role: 'guest' | 'user' | 'admin';
            is_verified: boolean;
            profile_picture_url?: string;
            created_at: string;
            updated_at: string;
        }>('/users/me', {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    /**
     * Change password
     */
    changePassword: async (data: { current_password: string; new_password: string }) => {
        return apiRequest<{
            message: string;
        }>('/users/change-password', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * List all users (admin only)
     */
    listUsers: async (params?: {
        skip?: number;
        limit?: number;
        role?: string;
        email_verified?: boolean;
    }) => {
        const queryParams = new URLSearchParams();
        if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
        if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
        if (params?.role) queryParams.append('role', params.role);
        if (params?.email_verified !== undefined) queryParams.append('email_verified', params.email_verified.toString());

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/users/?${queryString}` : '/users/';

        return apiRequest<{
            data: Array<{
                id: string;
                username: string;
                email: string;
                role: string;
                email_verified: boolean;
                created_at: string;
                updated_at: string;
            }>;
            total: number;
        }>(endpoint, {
            method: 'GET',
        });
    },

    /**
     * Update user role (admin only)
     */
    updateUserRole: async (userId: string, role: string) => {
        return apiRequest<{
            id: string;
            username: string;
            email: string;
            role: string;
            email_verified: boolean;
            created_at: string;
            updated_at: string;
        }>(`/users/${userId}/role`, {
            method: 'PATCH',
            body: JSON.stringify({ role }),
        });
    },

    /**
     * Verify user email manually (admin only)
     */
    verifyUserEmail: async (userId: string) => {
        return apiRequest<{
            id: string;
            username: string;
            email: string;
            role: string;
            email_verified: boolean;
            created_at: string;
            updated_at: string;
        }>(`/users/${userId}/verify-email`, {
            method: 'PATCH',
        });
    },

    /**
     * Delete user (admin only)
     */
    deleteUser: async (userId: string) => {
        return apiRequest<void>(`/users/${userId}`, {
            method: 'DELETE',
        });
    },
};
