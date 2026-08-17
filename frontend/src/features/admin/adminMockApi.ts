import type {
  AnalyzeDocumentRequest,
  CompareModelsRequest,
  LlmComparisonResult,
  OcrDocumentResult,
} from './types';

const SUPPORTED_EXTENSIONS = new Set(['pdf', 'png', 'jpg', 'jpeg']);

function delay(milliseconds: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));
}

function extensionOf(fileName: string) {
  return fileName.split('.').pop()?.toLowerCase() ?? '';
}

export async function analyzeDocumentMock(
  request: AnalyzeDocumentRequest,
): Promise<OcrDocumentResult> {
  await delay(800);

  if (!SUPPORTED_EXTENSIONS.has(extensionOf(request.file.name))) {
    throw new Error('PDF, PNG, JPG 형식만 문서 분석 테스트에 사용할 수 있습니다.');
  }

  const isPdf = extensionOf(request.file.name) === 'pdf';
  const pageCount = isPdf ? 4 : 1;
  const characterCount = isPdf ? 4_286 : 1_248;

  return {
    documentName: request.file.name,
    pageCount,
    characterCount,
    estimatedChunks: isPdf ? 11 : 4,
    confidence: isPdf ? 94.8 : 97.2,
    extractedText:
      '환자의 현재 증상과 과거 병력을 함께 검토해야 합니다. 문서에 포함된 검사 결과는 임상적 판단을 보조하기 위한 참고 자료이며, 최종 진단은 의료 전문가의 확인이 필요합니다. 복용 중인 약물과 알레르기 정보를 먼저 확인하고 필요한 추가 검사를 결정합니다.',
    chunks: [
      '[Chunk 01] 환자의 현재 증상과 과거 병력을 함께 검토해야 합니다. 문서에 포함된 검사 결과는 임상적 판단을 보조하기 위한 참고 자료입니다.',
      '[Chunk 02] 최종 진단은 의료 전문가의 확인이 필요합니다. 복용 중인 약물과 알레르기 정보를 먼저 확인하고 필요한 추가 검사를 결정합니다.',
    ],
    readiness: isPdf ? 'review' : 'ready',
    notes: isPdf
      ? ['표가 포함된 페이지는 열 순서를 확인해 주세요.', '개인정보가 포함되었는지 등록 전에 검토해 주세요.']
      : ['이미지 대비가 양호합니다.', '등록 전 추출 문장의 오탈자를 확인해 주세요.'],
  };
}

const ANSWERS: Record<string, string> = {
  medgemma:
    '제공된 정보만으로 확정적인 진단을 내리기보다 증상의 지속 기간, 복용 약물, 기저질환을 우선 확인해야 합니다. 위험 신호가 있다면 즉시 의료기관의 평가를 권고하고, 답변에는 참고 정보라는 한계를 명확히 표시하는 것이 좋습니다.',
  gemma:
    '문서의 핵심 근거를 증상, 검사 결과, 주의사항 순서로 정리할 수 있습니다. 사용자가 이해하기 쉬운 표현을 사용하되, 문서에 없는 내용을 추가하지 않고 필요한 경우 전문가 상담을 안내합니다.',
  qwen:
    '질문과 관련된 문서 조각을 먼저 선별한 뒤 공통적으로 반복되는 근거를 중심으로 답변을 구성합니다. 서로 충돌하는 내용은 하나로 단정하지 않고 확인이 필요한 항목으로 구분합니다.',
  llama:
    '질문의 의도를 먼저 요약하고 문서 근거를 항목별로 연결합니다. 마지막에는 답변의 제한 사항과 사용자가 다음으로 확인할 내용을 짧게 제시합니다.',
};

export async function compareModelsMock(
  request: CompareModelsRequest,
): Promise<LlmComparisonResult[]> {
  await delay(900);

  return request.modelIds.map((modelId, index) => {
    // Llama fixture는 부분 오류 카드의 UX를 확인하기 위한 의도적인 mock이다.
    if (modelId === 'llama') {
      return {
        modelId,
        status: 'error',
        error: 'Mock provider가 일시적으로 응답하지 않았습니다.',
        responseTimeSeconds: 8.74,
        inputTokens: 0,
        outputTokens: 0,
        chunkSize: request.chunkSize,
        overlap: request.overlap,
      };
    }

    const inputTokens = Math.max(64, Math.round(request.prompt.length * 1.7));
    return {
      modelId,
      status: 'success',
      answer: ANSWERS[modelId] ?? '선택한 모델의 mock 비교 응답입니다.',
      responseTimeSeconds: [6.42, 9.18, 13.52][index % 3],
      inputTokens,
      outputTokens: [186, 154, 203][index % 3],
      chunkSize: request.chunkSize,
      overlap: request.overlap,
    };
  });
}
