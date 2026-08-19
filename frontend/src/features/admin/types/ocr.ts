export type AnalyzeDocumentRequest = {
  file: File;
  chunkSize: number;
  overlap: number;
  signal?: AbortSignal;
};
export type SaveDocumentRequest = { documentName: string };
export type MockSaveResult = { message: string };

export type OcrProgressUpdate = {
  stage: string;
  progress: number;
  message: string;
};

export type OcrJobCreated = {
  jobId: string;
  status: 'queued';
};

export type OcrJobStatus = OcrProgressUpdate & {
  jobId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  result: OcrDocumentResult | null;
  error: string | null;
};

export type OcrProgressListener = (progress: OcrProgressUpdate) => void;

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
