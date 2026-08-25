import { OCR_SUPPORTED_EXTENSIONS } from '../constants/adminOptions';
import { LLM_MOCK_ANSWERS, MOCK_OUTPUT_TOKENS, MOCK_RESPONSE_TIMES } from '../mocks/llmMockData';
import { createOcrMockResult } from '../mocks/ocrMockData';
import type { CompareModelsRequest, LlmComparisonResult } from '../types/llm';
import type { AnalyzeDocumentRequest, MockSaveResult, OcrDocumentResult, SaveDocumentRequest } from '../types/ocr';

const delay = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));
const extensionOf = (fileName: string) => fileName.split('.').pop()?.toLowerCase() ?? '';

export const mockAdminAiService = {
  async analyzeDocument(request: AnalyzeDocumentRequest): Promise<OcrDocumentResult> {
    await delay(800);
    const extension = extensionOf(request.file.name);
    if (!OCR_SUPPORTED_EXTENSIONS.has(extension)) {
      throw new Error('PDF, PNG, JPG 형식만 문서 분석 테스트에 사용할 수 있습니다.');
    }
    return createOcrMockResult(request.file.name, extension === 'pdf');
  },

  async saveDocument(_request: SaveDocumentRequest): Promise<MockSaveResult> {
    await delay(450);
    return { message: '저장 테스트가 완료되었습니다. 실제 VectorDB에는 저장되지 않았습니다.' };
  },

  async compareModels(request: CompareModelsRequest): Promise<LlmComparisonResult[]> {
    await delay(900);
    return request.modelIds.map((modelId, index) => {
      if (modelId === 'llama') {
        return { modelId, status: 'error', error: 'Mock provider가 일시적으로 응답하지 않았습니다.', responseTimeSeconds: 8.74, inputTokens: 0, outputTokens: 0, chunkSize: request.chunkSize, overlap: request.overlap };
      }
      return {
        modelId, status: 'success', answer: LLM_MOCK_ANSWERS[modelId] ?? '선택한 모델의 mock 비교 응답입니다.',
        responseTimeSeconds: MOCK_RESPONSE_TIMES[index % MOCK_RESPONSE_TIMES.length],
        inputTokens: Math.max(64, Math.round(request.prompt.length * 1.7)),
        outputTokens: MOCK_OUTPUT_TOKENS[index % MOCK_OUTPUT_TOKENS.length],
        chunkSize: request.chunkSize, overlap: request.overlap,
      };
    });
  },
};
