import type { CompareModelsRequest, LlmComparisonResult } from '../types/llm';
import type { AnalyzeDocumentRequest, MockSaveResult, OcrDocumentResult, SaveDocumentRequest } from '../types/ocr';
import { mockAdminAiService } from './mockAdminAiService';

export interface AdminAiService {
  analyzeDocument(request: AnalyzeDocumentRequest): Promise<OcrDocumentResult>;
  saveDocument(request: SaveDocumentRequest): Promise<MockSaveResult>;
  compareModels(request: CompareModelsRequest): Promise<LlmComparisonResult[]>;
}

// 실제 API 연동 시 UI와 hook 대신 이 binding의 구현만 교체한다.
export const adminAiService: AdminAiService = mockAdminAiService;
