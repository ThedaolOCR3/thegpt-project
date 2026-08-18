import { apiClient } from '../../../services/apiClient';
import type { CompareModelsRequest, LlmComparisonResult } from '../types/llm';
import type {
  AnalyzeDocumentRequest,
  MockSaveResult,
  OcrDocumentResult,
  SaveDocumentRequest,
} from '../types/ocr';
import type { AdminAiService } from './adminAiService';

/**
 * Admin UI와 FastAPI 사이의 HTTP 변환 경계입니다.
 * 현재 단계에서는 파일 본문을 전송하지 않고 브라우저 File의 메타데이터만 전달합니다.
 */
export const apiAdminAiService: AdminAiService = {
  analyzeDocument(request: AnalyzeDocumentRequest) {
    return apiClient<OcrDocumentResult>('/admin/ocr/analyze', {
      method: 'POST',
      body: JSON.stringify({
        documentName: request.file.name,
        fileSize: request.file.size,
        contentType: request.file.type || null,
        chunkSize: request.chunkSize,
        overlap: request.overlap,
      }),
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
