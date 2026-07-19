import { apiRequest } from './client';

export interface ArenaRead {
  id: string;
  name: string;
  description?: string;
  game_type: string;
  config: Record<string, any>;
  packages?: 'numpy' | 'torch';
  has_password: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ArenaCreate {
  name: string;
  game_type: string;
  description?: string;
  config: Record<string, any>;
  packages?: 'numpy' | 'torch';
  password?: string;
  is_active: boolean;
}

export interface ArenaUpdate {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  packages?: 'numpy' | 'torch';
  password?: string;
  is_active?: boolean;
}

export const arenasApi = {
  getArenas: async () => {
    return apiRequest<ArenaRead[]>('/arenas', {
      method: 'GET',
    });
  },
  
  getArena: async (arenaId: string) => {
    return apiRequest<ArenaRead>(`/arenas/${arenaId}`, {
      method: 'GET',
    });
  },

  createArena: async (data: ArenaCreate) => {
    return apiRequest<ArenaRead>('/arenas', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateArena: async (arenaId: string, data: ArenaUpdate) => {
    return apiRequest<ArenaRead>(`/arenas/${arenaId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  deleteArena: async (arenaId: string) => {
    return apiRequest<void>(`/arenas/${arenaId}`, {
      method: 'DELETE',
    });
  },
};
