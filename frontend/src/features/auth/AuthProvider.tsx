import { useEffect, useState, type ReactNode } from 'react';
import { authApi } from './authApi';
import { AuthContext } from './AuthContext';
import { authStorage } from './authStorage';
import type { User } from './types';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = authStorage.getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    // 새로고침 시 저장된 토큰을 서버에서 검증합니다.
    authApi.getMe(token)
      .then(setUser)
      .catch(() => authStorage.clearToken())
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    authStorage.setToken(result.access_token);
    setUser(result.user);
  };

  const logout = () => {
    authStorage.clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
