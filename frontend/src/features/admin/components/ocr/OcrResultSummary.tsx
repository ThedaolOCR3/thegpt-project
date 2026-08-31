import { Check, FileText } from "lucide-react";
import type { AsyncStatus } from "../../types/common";
import type { OcrDocumentResult, OcrProgressUpdate } from "../../types/ocr";

export function OcrResultSummary({
  status,
  progress,
  result,
  saveStatus,
  saveMessage,
  onSave,
}: {
  status: AsyncStatus;
  progress: OcrProgressUpdate;
  result: OcrDocumentResult | null;
  saveStatus: AsyncStatus;
  saveMessage: string;
  onSave: () => void;
}) {
  if (status === "loading")
    return (
      <div className="admin-loading-state">
        <span className="loading-orbit" />
        <div className="ocr-progress-shell">
          <div className="ocr-progress-heading">
            <strong>{progress.message}</strong>
            <span>{progress.progress}%</span>
          </div>
          <div
            className="ocr-progress-track"
            role="progressbar"
            aria-label="OCR 분석 진행률"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress.progress}
          >
            <span
              className="ocr-progress-bar"
              style={{ width: `${progress.progress}%` }}
            />
          </div>
          <p>문서 구조 분석부터 텍스트 정제와 Chunk 생성까지 진행합니다.</p>
        </div>
      </div>
    );
  if (!result)
    return (
      <div className="admin-empty-state">
        <FileText size={34} />
        <strong>분석 결과가 여기에 표시됩니다</strong>
        <p>문서를 선택하고 분석 테스트를 실행해 주세요.</p>
      </div>
    );
  const extension = result.documentName.split(".").pop()?.toLowerCase();
  const unitLabel = result.sourceType === "url" ? "출처" : extension === "pptx" ? "슬라이드" : "페이지";
  return (
    <div className="ocr-result">
      <div className="result-title-row">
        <div>
          <span>분석 완료</span>
          <h3>{result.documentName}</h3>
          {result.sourceType === "url" && result.sourceUrl && (
            <a className="result-source-link" href={result.sourceUrl} target="_blank" rel="noopener noreferrer">
              원문 웹페이지 열기
            </a>
          )}
        </div>
        <span className={`readiness-badge ${result.readiness}`}>
          <Check size={13} />{" "}
          {result.readiness === "ready" ? "등록 가능" : "검토 필요"}
        </span>
      </div>
      <dl className="metric-grid">
        <div>
          <dt>{unitLabel}</dt>
          <dd>{result.sourceType === "url" ? "WEB" : result.pageCount ?? "계산 안 됨"}</dd>
        </div>
        <div>
          <dt>추출 문자</dt>
          <dd>{result.characterCount.toLocaleString()}</dd>
        </div>
        <div>
          <dt>예상 Chunk</dt>
          <dd>{result.estimatedChunks}</dd>
        </div>
        <div>
          <dt>인식 신뢰도</dt>
          <dd>{result.confidence}%</dd>
        </div>
      </dl>
      <TextPreview
        title="추출 텍스트 미리보기"
        texts={[result.extractedText]}
      />
      <TextPreview title="Chunked Text" texts={result.chunks} chunked />
      <div className="quality-note">
        <strong>품질 확인 메모</strong>
        <ul>
          {result.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </div>
      <button
        className="admin-primary-button"
        type="button"
        onClick={onSave}
        disabled={saveStatus === "loading" || saveStatus === "success"}
      >
        {saveStatus === "loading"
          ? "VectorDB 저장 중..."
          : saveStatus === "success"
            ? "VectorDB 저장 완료"
            : "VectorDB에 저장"}
      </button>
      {saveMessage && (
        <p
          className={saveStatus === "error" ? "admin-error" : "admin-success"}
          role="status"
        >
          {saveMessage}
        </p>
      )}
    </div>
  );
}

function TextPreview({
  title,
  texts,
  chunked = false,
}: {
  title: string;
  texts: string[];
  chunked?: boolean;
}) {
  return (
    <div className="result-block">
      <h4>{title}</h4>
      {chunked ? (
        <div className="chunk-list">
          {texts.map((text, index) => (
            <p key={`${index}-${text.slice(0, 24)}`}>{text}</p>
          ))}
        </div>
      ) : (
        <p>{texts[0]}</p>
      )}
    </div>
  );
}
