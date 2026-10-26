/** Сотрудник, вошедший в админку: права роли определяют, какие разделы и кнопки видны (ADM-01). */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, setCsrf, UNAUTHORIZED } from './api';
import type { Me } from './types';

interface Auth {
  me: Me | null;
  loading: boolean;
  can: (permission: string) => boolean;
  signedIn: (me: Me) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<Auth>({ me: null, loading: true, can: () => false, signedIn: () => undefined, signOut: async () => undefined });

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const [expired, setExpired] = useState(false);
  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        const data = await api.get<Me>('/auth/me');
        setCsrf(data.csrfToken);
        return data;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    const onExpired = () => {
      setExpired(true);
      client.setQueryData(['me'], null);
    };
    window.addEventListener(UNAUTHORIZED, onExpired);
    return () => window.removeEventListener(UNAUTHORIZED, onExpired);
  }, [client]);

  const value: Auth = {
    me: expired ? null : (me.data ?? null),
    loading: me.isLoading,
    can: (permission) => !!me.data?.permissions.includes(permission),
    signedIn: (data) => {
      setCsrf(data.csrfToken);
      setExpired(false);
      client.setQueryData(['me'], data);
    },
    signOut: async () => {
      await api.post('/auth/logout').catch(() => undefined);
      client.clear();
      client.setQueryData(['me'], null);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
