import { useEffect, useRef } from "react";
import { FileText, LoaderCircle, RotateCcw, X } from "lucide-react";

type Props = {
  prompt: string;
  file: File | null;
  isRunningAll: boolean;
  hasRunningModels: boolean;
  isLoadingModels: boolean;
  hasRunnableModels: boolean;
  error: string;
  onPromptChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  onRunAll: () => void;
  onReset: () => void;
};

export function LlmTestForm(props: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!props.file && fileRef.current) fileRef.current.value = "";
  }, [props.file]);

  return (
    <div className="admin-card llm-form-card">
      <label className="admin-field">
        <span>공통 질문 / Prompt</span>
        <textarea
          value={props.prompt}
          onChange={(event) => props.onPromptChange(event.target.value)}
          placeholder="예: 이 의료 문서의 핵심 내용을 근거 중심으로 요약해 주세요."
          rows={4}
        />
      </label>

      <div className="llm-reference-field">
        <div className="llm-attachment-row">
          <button
            className="admin-secondary-button"
            type="button"
            onClick={() => fileRef.current?.click()}
          >
            <FileText size={16} /> RAG 참고 문서 선택
          </button>
          <input
            ref={fileRef}
            className="admin-visually-hidden"
            type="file"
            aria-label="LLM 비교 RAG 참고 문서 선택"
            onChange={(event) =>
              props.onFileChange(event.target.files?.[0] ?? null)
            }
          />
          {props.file && (
            <span className="file-chip">
              {props.file.name}
              <button
                type="button"
                aria-label="참고 문서 제거"
                onClick={() => props.onFileChange(null)}
              >
                <X size={13} />
              </button>
            </span>
          )}
        </div>
        <small>
          파일 내용은 아직 업로드되지 않습니다. 모든 모델에는 파일명 조건만
          동일하게 전달됩니다.
        </small>
      </div>

      {props.error && (
        <p className="admin-error" role="alert">
          {props.error}
        </p>
      )}

      <div className="llm-form-actions">
        <button
          className="admin-primary-button llm-run-all-button"
          type="button"
          onClick={props.onRunAll}
          disabled={
            props.hasRunningModels ||
            props.isRunningAll ||
            props.isLoadingModels ||
            !props.hasRunnableModels
          }
          aria-busy={props.isRunningAll}
        >
          {props.isRunningAll ? (
            <>
              <LoaderCircle className="spin" size={17} /> 전체 모델 실행 중...
            </>
          ) : props.isLoadingModels ? (
            "모델 목록 확인 중..."
          ) : props.hasRunningModels ? (
            "개별 모델 실행 중..."
          ) : !props.hasRunnableModels ? (
            "실행 가능한 모델 없음"
          ) : (
            "전체 모델 비교 시작"
          )}
        </button>
        <button
          className="admin-secondary-button llm-reset-button"
          type="button"
          onClick={props.onReset}
        >
          <RotateCcw size={16} /> 입력 및 결과 초기화
        </button>
      </div>
    </div>
  );
}
