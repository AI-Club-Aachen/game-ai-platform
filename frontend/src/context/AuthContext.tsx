import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { usersApi } from '../services/api/users';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'guest' | 'user' | 'admin';
  is_verified?: boolean;
  profile_picture_url?: string;
  created_at?: string;
  updated_at?: string;
}

interface AuthContextType {
  user: User | null;
  isAdmin: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    const token = localStorage.getItem('access_token');

    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const userData = await usersApi.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to restore auth session:', error);
      logout(); // Clear invalid token
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (token: string) => {
    localStorage.setItem('access_token', token);
    try {
      // Fetch full user details immediately after setting token
      const userData = await usersApi.getCurrentUser();
      setUser(userData);
      localStorage.setItem('user_id', userData.id);
    } catch (error) {
      console.error('Failed to fetch user details during login:', error);
      // Even if fetching user fails, we keep the token? 
      // Or should we fail the login? 
      // For now, let's allow it but user state might be partial if we didn't fetch it.
      // Actually, better to throw so the UI knows login "failed" effectively if we can't get user.
      logout();
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    setUser(null);
  };

  const value = {
    user,
    isAdmin: user?.role === 'admin',
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshUser: checkUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
