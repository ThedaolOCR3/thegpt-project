import { API_URL, apiClient } from '../../services/apiClient';
import type { LoginResponse, User } from './types';

export type OAuthProvider = 'google' | 'github';

export const authApi = {
  login: (email: string, password: string) =>
    apiClient<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  getMe: (token: string) => apiClient<User>('/auth/me', { token }),

  // 버튼 클릭 시 이 주소로 풀페이지 이동(window.location.href)한다 - 백엔드가
  // Google/GitHub 동의 화면으로 다시 리다이렉트해준다. fetch가 아니라 브라우저
  // 자체 이동이어야 실제 로그인 화면(팝업 아님)으로 넘어간다.
  oauthLoginUrl: (provider: OAuthProvider) => `${API_URL}/auth/oauth/${provider}/authorize`,
};
