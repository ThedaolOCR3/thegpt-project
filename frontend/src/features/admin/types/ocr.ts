export type AnalyzeDocumentRequest = { file: File; chunkSize: number; overlap: number };
export type SaveDocumentRequest = { documentName: string };
export type MockSaveResult = { message: string };

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
