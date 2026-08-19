import type { CompareModelsRequest, LlmComparisonResult } from '../types/llm';
import type {
  AnalyzeDocumentRequest,
  MockSaveResult,
  OcrDocumentResult,
  OcrProgressListener,
  SaveDocumentRequest,
} from '../types/ocr';
import { apiAdminAiService } from './apiAdminAiService';

export interface AdminAiService {
  analyzeDocument(request: AnalyzeDocumentRequest, onProgress?: OcrProgressListener): Promise<OcrDocumentResult>;
  saveDocument(request: SaveDocumentRequest): Promise<MockSaveResult>;
  compareModels(request: CompareModelsRequest): Promise<LlmComparisonResult[]>;
}

// UI와 hook은 HTTP 세부사항을 알지 않고 이 Service 계약만 사용합니다.
export const adminAiService: AdminAiService = apiAdminAiService;
