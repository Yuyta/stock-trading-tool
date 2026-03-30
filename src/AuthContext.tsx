import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthState } from './types';

interface AuthContextType extends AuthState {
  login: (token: string, user: User) => void;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'stock_analyzer_token';
const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: localStorage.getItem(TOKEN_KEY),
    isLoading: true,
  });

  useEffect(() => {
    const initAuth = async () => {
      if (!state.token) {
        setState(prev => ({ ...prev, isLoading: false }));
        return;
      }

      try {
        const resp = await fetch(`${API_BASE}/api/me`, {
          headers: {
            'Authorization': `Bearer ${state.token}`
          }
        });
        if (resp.ok) {
          const user = await resp.json();
          setState(prev => ({ ...prev, user, isLoading: false }));
        } else {
          // Token expired or invalid
          logout();
        }
      } catch (e) {
        console.error('Auth initialization failed', e);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    initAuth();
  }, [state.token]);

  const login = (token: string, user: User) => {
    localStorage.setItem(TOKEN_KEY, token);
    setState({ token, user, isLoading: false });
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setState({ token: null, user: null, isLoading: false });
  };

  const setUser = (user: User | null) => {
    setState(prev => ({ ...prev, user }));
  };

  return (
    <AuthContext.Provider value={{ ...state, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
