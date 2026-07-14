import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import apiClient from '../services/apiClient';

interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  role: {
    id: number;
    name: string;
  };
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (access_token: string, refresh_token: string, user_data: User) => void;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const login = (access_token: string, refresh_token: string, user_data: User) => {
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    setUser(user_data);
  };

  const logout = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch (error) {
      console.error('Logout error', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    }
  };

  const checkSession = async () => {
    setIsLoading(true);
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const response = await apiClient.get('/auth/me');
        setUser(response.data);
      } catch (error) {
        // Interceptor handles the token clearing on permanent failure
        setUser(null);
      }
    }
    setIsLoading(false);
  };

  useEffect(() => {
    checkSession();
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout, checkSession }}>
      {children}
    </AuthContext.Provider>
  );
};
