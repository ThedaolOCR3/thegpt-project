const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

interface RequestOptions extends RequestInit {
  token?: string | null;
}

// status를 붙여서, 호출하는 쪽에서 401(만료/무효 토큰)인지 구분해 재시도 같은 처리를
//할 수 있게 한다 (guestSession.ts의 자동 게스트 재발급이 이걸 씀).
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function apiClient<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers, ...requestOptions } = options;
  const response = await fetch(`${API_URL}${path}`, {
    ...requestOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail ?? '요청을 처리하지 못했습니다.', response.status);
  }
  return response.json() as Promise<T>;
}
