/**
 * API Service for the Game AI Platform
 * Handles all communication with the backend API
 */

// Base API URL - adjust based on environment
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Generic API error class
 */
export class ApiError extends Error {
    constructor(message: string, public status?: number) {
        super(message);
        this.name = 'ApiError';
    }
}

/**
 * Makes an API request with error handling
 */
export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
    const token = localStorage.getItem('access_token');

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };

    // Merge custom headers from options
    if (options.headers) {
        Object.entries(options.headers).forEach(([key, value]) => {
            headers[key] = value as string;
        });
    }

    if (token && !options.skipAuth) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

            try {
                const errorData = await response.json();
                if (errorData.detail && Array.isArray(errorData.detail)) {
                    // Handle Pydantic validation errors (array of objects)
                    errorMessage = errorData.detail
                        .map((err: any) => err.msg || JSON.stringify(err))
                        .join('. ');
                } else {
                    // Handle standard error message (string or other)
                    errorMessage = errorData.detail || errorData.message || errorMessage;
                }
            } catch {
                // If error response is not JSON, use status text
            }

            throw new ApiError(errorMessage, response.status);
        }

        // Handle empty responses
        const text = await response.text();
        return text ? JSON.parse(text) : ({} as T);
    } catch (error) {
        if (error instanceof ApiError) {
            throw error;
        }

        // Network error or other issue
        throw new ApiError(
            error instanceof Error ? error.message : 'An unexpected error occurred'
        );
    }
}
