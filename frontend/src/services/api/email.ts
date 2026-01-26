import { apiRequest } from './client';

/**
 * Email Verification API
 */
export const emailApi = {
    /**
     * Verify email with token
     */
    verifyEmail: async (token: string) => {
        return apiRequest<{
            message: string;
        }>('/email/verify-email', {
            method: 'POST',
            body: JSON.stringify({ token }),
        });
    },

    /**
     * Resend verification email
     */
    resendVerification: async (email: string) => {
        return apiRequest<{
            message: string;
        }>('/email/resend-verification', {
            method: 'POST',
            body: JSON.stringify({ email }),
            skipAuth: true,
        });
    },

    /**
     * Check verification status
     */
    checkVerificationStatus: async () => {
        return apiRequest<{
            is_verified: boolean;
        }>('/email/verification-status', {
            method: 'GET',
        });
    },
};
