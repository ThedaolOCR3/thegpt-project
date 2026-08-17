export type AdminTab = 'ocr' | 'llm';

export type AnalyzeDocumentRequest = {
  file: File;
};

export type OcrDocumentResult = {
  documentName: string;
  pageCount: number;
  characterCount: number;
  estimatedChunks: number;
  confidence: number;
  extractedText: string;
  chunks: string[];
  readiness: 'review' | 'ready';
  notes: string[];
};

export type CompareModelsRequest = {
  prompt: string;
  modelIds: string[];
  file?: File;
  chunkSize: number;
  overlap: number;
};

export type LlmComparisonResult = {
  modelId: string;
  status: 'success' | 'error';
  answer?: string;
  error?: string;
  responseTimeSeconds: number;
  inputTokens: number;
  outputTokens: number;
  chunkSize: number;
  overlap: number;
};
