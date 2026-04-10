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
    created_at: string;
    updated_at: string;
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

        return apiRequest<AgentContainerRead[]>(endpoint, { method: 'GET' });
    },
};
