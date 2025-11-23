/**
 * API Service for the Game AI Platform
 * Handles all communication with the backend API
 */

// Base API URL - adjust based on environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Generic API error class
 */
class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Makes an API request with error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
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

  if (token) {
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
        errorMessage = errorData.detail || errorData.message || errorMessage;
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
   * Verify email with token
   */
  verifyEmail: async (token: string) => {
    return apiRequest<{
      message: string;
    }>(`/auth/verify-email?token=${encodeURIComponent(token)}`, {
      method: 'GET',
    });
  },

  /**
   * Get current user profile
   */
  getCurrentUser: async () => {
    return apiRequest<{
      id: string;
      username: string;
      email: string;
      is_verified: boolean;
    }>('/auth/me', {
      method: 'GET',
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

/**
 * Matches API
 */
export const matchesApi = {
  /**
   * Get all matches
   */
  getMatches: async (params?: { game_id?: string; user_id?: string }) => {
    const queryParams = new URLSearchParams();
    if (params?.game_id) queryParams.append('game_id', params.game_id);
    if (params?.user_id) queryParams.append('user_id', params.user_id);

    const queryString = queryParams.toString();
    const endpoint = queryString ? `/matches?${queryString}` : '/matches';

    return apiRequest<Array<{
      id: string;
      game_id: string;
      status: string;
      created_at: string;
      completed_at?: string;
      result?: any;
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
      game_id: string;
      status: string;
      created_at: string;
      completed_at?: string;
      result?: any;
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
    game_id: string;
    player_submissions: string[];
  }) => {
    return apiRequest<{
      match_id: string;
      message: string;
    }>('/matches', {
      method: 'POST',
      body: JSON.stringify(matchData),
    });
  },
};

/**
 * Submissions API
 */
export const submissionsApi = {
  /**
   * Get all submissions for the current user
   */
  getSubmissions: async () => {
    return apiRequest<Array<{
      id: string;
      game_id: string;
      user_id: string;
      code: string;
      status: string;
      created_at: string;
    }>>('/submissions', {
      method: 'GET',
    });
  },

  /**
   * Submit agent code for a game
   */
  submitAgent: async (submissionData: {
    game_id: string;
    code: string;
    language?: string;
  }) => {
    return apiRequest<{
      submission_id: string;
      message: string;
    }>('/submissions', {
      method: 'POST',
      body: JSON.stringify(submissionData),
    });
  },

  /**
   * Get a specific submission by ID
   */
  getSubmission: async (submissionId: string) => {
    return apiRequest<{
      id: string;
      game_id: string;
      user_id: string;
      code: string;
      status: string;
      created_at: string;
    }>(`/submissions/${submissionId}`, {
      method: 'GET',
    });
  },
};

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

export { ApiError };
