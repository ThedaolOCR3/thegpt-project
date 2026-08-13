import { apiClient } from '../../services/apiClient';
import { authStorage } from '../auth/authStorage';

export interface UsageSummary {
  consultation_count: number;
  last_consultation_at: string | null;
}

export const myPageApi = {
  getUsage: () => apiClient<UsageSummary>('/auth/me/usage', { token: authStorage.getToken() }),
  deleteAccount: (password: string) => apiClient<{ message: string }>('/auth/me', {
    method: 'DELETE', token: authStorage.getToken(), body: JSON.stringify({ password }),
  }),
  deleteAllConsultations: () => apiClient<{ message: string; deleted_count: number }>(
    '/auth/me/consultations',
    { method: 'DELETE', token: authStorage.getToken() },
  ),
};
