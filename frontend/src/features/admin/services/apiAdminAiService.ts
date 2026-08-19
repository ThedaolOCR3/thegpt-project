import { apiClient } from '../../../services/apiClient';
import type { CompareModelsRequest, LlmComparisonResult } from '../types/llm';
import type {
  AnalyzeDocumentRequest,
  MockSaveResult,
  OcrDocumentResult,
  SaveDocumentRequest,
} from '../types/ocr';
import type { AdminAiService } from './adminAiService';

/** Admin UI와 FastAPI 사이의 HTTP 변환 경계입니다. */
export const apiAdminAiService: AdminAiService = {
  analyzeDocument(request: AnalyzeDocumentRequest) {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('chunkSize', String(request.chunkSize));
    formData.append('overlap', String(request.overlap));

    return apiClient<OcrDocumentResult>('/admin/ocr/analyze', {
      method: 'POST',
      body: formData,
    });
  },

  saveDocument(request: SaveDocumentRequest) {
    return apiClient<MockSaveResult>('/admin/ocr/vector-save-test', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  compareModels(request: CompareModelsRequest) {
    return apiClient<LlmComparisonResult[]>('/admin/llm/compare', {
      method: 'POST',
      body: JSON.stringify({
        prompt: request.prompt,
        modelIds: request.modelIds,
        documentName: request.file?.name ?? null,
        chunkSize: request.chunkSize,
        overlap: request.overlap,
      }),
    });
  },
};
