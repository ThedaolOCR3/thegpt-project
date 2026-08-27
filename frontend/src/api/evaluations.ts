import { apiClient } from '../services/apiClient';

export interface RetrievalEvalResult {
  numQueries: number;
  recallAtK: Record<string, number>;
  mrr: number;
  datasetName: string;
}

/**
 * corpus/쿼리 임베딩을 새로 계산하므로(캐시 없음) 수십 초~수 분 걸릴 수 있다 —
 * 호출하는 쪽에서 반드시 로딩 상태를 보여줘야 한다.
 */
export function runRetrievalEvaluation(signal?: AbortSignal): Promise<RetrievalEvalResult> {
  return apiClient<RetrievalEvalResult>('/admin/evaluations/retrieval', { signal });
}
