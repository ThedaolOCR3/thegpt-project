import { apiClient } from '../../../services/apiClient';
import { authStorage } from '../../auth/authStorage';
import type { LlmModelDefinition, LlmModelResult, RunLlmModelRequest } from '../types/llm';
import type {
  AnalyzeDocumentRequest,
  OcrDocumentResult,
  OcrJobCreated,
  OcrJobStatus,
  OcrProgressListener,
  SaveDocumentRequest,
  SaveDocumentResult,
} from '../types/ocr';
import type { AdminAiService } from './adminAiService';

const OCR_JOB_POLL_INTERVAL_MS = 700;

function waitForNextPoll(signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('OCR 상태 조회가 취소되었습니다.', 'AbortError'));
      return;
    }

    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', handleAbort);
      resolve();
    }, OCR_JOB_POLL_INTERVAL_MS);
    const handleAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException('OCR 상태 조회가 취소되었습니다.', 'AbortError'));
    };
    signal?.addEventListener('abort', handleAbort, { once: true });
  });
}

/** Admin UI와 FastAPI 사이의 HTTP 변환 경계입니다. */
export const apiAdminAiService: AdminAiService = {
  async analyzeDocument(request: AnalyzeDocumentRequest, onProgress?: OcrProgressListener) {
    const job = request.sourceType === 'file'
      ? await createFileJob(request)
      : await createUrlJob(request);
    onProgress?.({ stage: 'queued', progress: 0, message: 'OCR 작업이 대기열에 등록되었습니다.' });

    while (true) {
      const status = await apiClient<OcrJobStatus>(`/admin/ocr/jobs/${encodeURIComponent(job.jobId)}`, {
        signal: request.signal,
      });
      onProgress?.({ stage: status.stage, progress: status.progress, message: status.message });

      if (status.status === 'completed') {
        if (!status.result) throw new Error('완료된 OCR 작업에 분석 결과가 없습니다.');
        // 저장 시 Chunk를 다시 보내지 않고 Backend의 완료된 Job 결과를 참조합니다.
        return { ...status.result, jobId: status.jobId };
      }
      if (status.status === 'failed') {
        throw new Error(status.error ?? 'OCR 문서 분석에 실패했습니다.');
      }
      await waitForNextPoll(request.signal);
    }
  },

  saveDocument(request: SaveDocumentRequest) {
    return apiClient<SaveDocumentResult>('/admin/ocr/vector-save', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  listLlmModels(signal?: AbortSignal) {
    return apiClient<LlmModelDefinition[]>('/admin/llm/models', { signal });
  },

  runLlmModel(request: RunLlmModelRequest) {
    return apiClient<LlmModelResult>('/admin/llm/run', {
      method: 'POST',
      body: JSON.stringify({
        prompt: request.prompt,
        modelId: request.modelId,
        documentNames: request.files?.map((file) => file.name) ?? [],
      }),
      signal: request.signal,
    });
  },
};

async function createFileJob(
  request: Extract<AnalyzeDocumentRequest, { sourceType: 'file' }>,
): Promise<OcrJobCreated> {
  const formData = new FormData();
  formData.append('file', request.file);
  formData.append('chunkSize', String(request.chunkSize));
  formData.append('overlap', String(request.overlap));
  return apiClient<OcrJobCreated>('/admin/ocr/jobs', {
    method: 'POST',
    body: formData,
    signal: request.signal,
  });
}

async function createUrlJob(
  request: Extract<AnalyzeDocumentRequest, { sourceType: 'url' }>,
): Promise<OcrJobCreated> {
  return apiClient<OcrJobCreated>('/admin/ocr/url-jobs', {
    method: 'POST',
    body: JSON.stringify({
      url: request.url,
      chunkSize: request.chunkSize,
      overlap: request.overlap,
    }),
    signal: request.signal,
    token: authStorage.getToken(),
  });
}
