import { createContext, useContext, useState, type ReactNode } from 'react';

type AuthContextValue = {
  isLoggedIn: boolean;
  userId: string;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const GUEST_ID_KEY = 'thegpt-guest-id';

function getOrCreateGuestId(): string {
  const stored = localStorage.getItem(GUEST_ID_KEY);
  if (stored) return stored;
  const id = `user_${Math.floor(10000 + Math.random() * 90000)}`;
  localStorage.setItem(GUEST_ID_KEY, id);
  return id;
}

// 실제 로그인 연동 전까지의 mock. 지금은 항상 비로그인 상태로 시작하고
// user_XXXXX 형태의 guest id를 부여한다. 로그인 붙으면 이 Provider 내부만 교체하면 됨.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [value] = useState<AuthContextValue>(() => ({
    isLoggedIn: false,
    userId: getOrCreateGuestId(),
  }));

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth는 AuthProvider 안에서만 사용할 수 있습니다.');
  return context;
}
