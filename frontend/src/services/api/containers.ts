import { apiRequest } from './client';

export interface AgentContainerRead {
    id: string;
    container_id: string;
    match_id: string | null;
    agent_id: string;
    agent_name: string | null;
    name: string | null;
    status: 'running' | 'stopped' | 'error' | string;
    image: string;
    uptime_seconds: number;
    cpu_percent: number;
    memory_mb: number;
    logs: string | null;
    created_at: string;
    updated_at: string;
}

/**
 * Paginated container list envelope. `total` and `status_counts` cover the whole
 * filtered set (not just the page), so the UI can paginate accurately and show
 * global summaries. The backend caps `limit` at 100 (SECURITY.md M-4).
 */
export interface AgentContainerListResponse {
    data: AgentContainerRead[];
    total: number;
    skip: number;
    limit: number;
    status_counts: Record<string, number>;
}

export const containersApi = {
    getContainers: async (params?: { match_id?: string; status?: string; skip?: number; limit?: number }) => {
        const queryParams = new URLSearchParams();
        if (params?.match_id) queryParams.append('match_id', params.match_id);
        if (params?.status) queryParams.append('status', params.status);
        if (params?.skip !== undefined) queryParams.append('skip', String(params.skip));
        if (params?.limit !== undefined) queryParams.append('limit', String(params.limit));

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/agent_containers?${queryString}` : '/agent_containers';

        return apiRequest<AgentContainerListResponse>(endpoint, { method: 'GET' });
    },

    getMatchContainers: async (matchId: string) => {
        const queryParams = new URLSearchParams();
        queryParams.append('match_id', matchId);
        queryParams.append('limit', '10');
        const response = await apiRequest<AgentContainerListResponse>(
            `/agent_containers?${queryParams.toString()}`,
            { method: 'GET' },
        );
        return response.data;
    },
};
