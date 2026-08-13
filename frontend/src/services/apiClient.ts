const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

interface RequestOptions extends RequestInit {
  token?: string | null;
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
    throw new Error(body?.detail ?? '요청을 처리하지 못했습니다.');
  }
  return response.json() as Promise<T>;
}
