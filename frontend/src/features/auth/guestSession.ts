import { apiClient } from '../../services/apiClient';
import { authStorage } from './authStorage';
import type { LoginResponse } from './types';

const GUEST_TOKEN_KEY = 'thegpt_guest_token';

let inFlight: Promise<string> | null = null;

/**
 * 채팅 API 호출에 쓸 토큰을 가져온다.
 * 로그인한 사용자는 자신의 토큰을, 아니면 서버가 발급하는 게스트 토큰을 브라우저에
 * 오래 캐시해두고 재사용한다 (재방문 시 같은 게스트 계정으로 이어짐).
 * mypage 등 실제 로그인이 필요한 화면과는 무관 — AuthContext.user는 건드리지 않는다.
 */
export async function getChatToken(): Promise<string> {
  const userToken = authStorage.getToken();
  if (userToken) return userToken;

  const cachedGuestToken = localStorage.getItem(GUEST_TOKEN_KEY);
  if (cachedGuestToken) return cachedGuestToken;

  if (!inFlight) {
    inFlight = apiClient<LoginResponse>('/auth/guest', { method: 'POST' })
      .then((response) => {
        localStorage.setItem(GUEST_TOKEN_KEY, response.access_token);
        return response.access_token;
      })
      .finally(() => {
        inFlight = null;
      });
  }
  return inFlight;
}
