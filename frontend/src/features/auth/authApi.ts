import { apiClient } from '../../services/apiClient';
import type { LoginResponse, User } from './types';

export const authApi = {
  login: (email: string, password: string) =>
    apiClient<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  getMe: (token: string) => apiClient<User>('/auth/me', { token }),
};
