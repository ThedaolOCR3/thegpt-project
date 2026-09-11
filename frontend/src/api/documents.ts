import { apiClient } from '../services/apiClient';
import { withChatToken } from '../features/auth/guestSession';

interface OcrLineDto {
  text: string;
  confidence: number;
}

interface OcrResponseDto {
  text: string;
  lines: OcrLineDto[];
}

/**
 * 문서에서 텍스트를 추출한다 (DocumentPreviewPanel에서 호출).
 * 이미지뿐 아니라 PDF·DOCX·PPTX·TXT·CSV·JSON(L)·ZIP도 지원한다 — 실제 지원 형식은
 * ai/ocr/validation.py의 SUPPORTED_* 상수를 따른다. 파일은 서버에 저장되지 않고
 * OCR/텍스트 추출 결과만 즉시 돌아온다.
 */
export async function extractDocumentText(file: File): Promise<OcrResponseDto> {
  const formData = new FormData();
  formData.append('file', file);
  return withChatToken((token) =>
    apiClient<OcrResponseDto>('/documents/ocr', { method: 'POST', token, body: formData }),
  );
}
