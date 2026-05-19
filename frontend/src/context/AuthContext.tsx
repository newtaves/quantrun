import React, { createContext, useState, useEffect, useContext } from 'react';
import { DJANGO_API_URL } from '../config';

interface User {
  id: number;
  username: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load persisted session on startup
    const storedUser = localStorage.getItem('qr_user');
    const storedToken = localStorage.getItem('qr_token');
    
    if (storedUser && storedToken) {
      setUser(JSON.parse(storedUser));
      setToken(storedToken);
    }
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    setError(null);
    try {
      const resp = await fetch(`${DJANGO_API_URL}/api/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      
      const data = await resp.json();
      
      if (!resp.ok) {
        throw new Error(data.detail || 'Login failed. Please check credentials.');
      }
      
      setUser(data.user);
      setToken(data.token);
      localStorage.setItem('qr_user', JSON.stringify(data.user));
      localStorage.setItem('qr_token', data.token);
    } catch (e: any) {
      setError(e.message || 'Network error occurred');
      throw e;
    }
  };

  const signup = async (username: string, password: string) => {
    setError(null);
    try {
      const resp = await fetch(`${DJANGO_API_URL}/api/signup/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      
      const data = await resp.json();
      
      if (!resp.ok) {
        throw new Error(data.detail || 'Signup failed.');
      }
      
      setUser(data.user);
      setToken(data.token);
      localStorage.setItem('qr_user', JSON.stringify(data.user));
      localStorage.setItem('qr_token', data.token);
    } catch (e: any) {
      setError(e.message || 'Network error occurred');
      throw e;
    }
  };

  const logout = async () => {
    // Revoke token on Django side (best effort)
    if (token) {
      try {
        await fetch(`${DJANGO_API_URL}/api/logout/`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` 
          },
        });
      } catch (e) {
        console.warn('Failed to revoke token on logout', e);
      }
    }
    
    // Clear state
    setUser(null);
    setToken(null);
    localStorage.removeItem('qr_user');
    localStorage.removeItem('qr_token');
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, signup, logout, error, clearError }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
