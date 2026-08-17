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
