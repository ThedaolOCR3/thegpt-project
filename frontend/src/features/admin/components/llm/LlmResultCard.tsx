import { useState } from "react";
import { Check, Clipboard, LoaderCircle, X } from "lucide-react";
import { getModelOption } from "../../../../components/Chat/modelOptions";
import type { LlmComparisonResult } from "../../types/llm";

export function LoadingModelCard({ modelId }: { modelId: string }) {
  return (
    <article className="admin-card model-result-card loading-card">
      <div className="model-card-header">
        <h3>{getModelOption(modelId).label}</h3>
        <span>
          <LoaderCircle className="spin" size={14} /> 생성 중
        </span>
      </div>
      <div className="skeleton-line wide" />
      <div className="skeleton-line" />
      <div className="skeleton-line short" />
    </article>
  );
}

export function LlmResultCard({ result }: { result: LlmComparisonResult }) {
  const [copied, setCopied] = useState(false);
  const model = getModelOption(result.modelId);
  async function copy() {
    if (!result.answer) return;
    await navigator.clipboard.writeText(result.answer);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }
  return (
    <article className={`admin-card model-result-card ${result.status}`}>
      <div className="model-card-header">
        <div>
          <span>{model.tier}</span>
          <h3>{model.label}</h3>
        </div>
        <span className={`model-status ${result.status}`}>
          {result.status === "success" ? <Check size={13} /> : <X size={13} />}
          {result.status === "success" ? "성공" : "오류"}
        </span>
      </div>
      {result.status === "success" ? (
        <>
          <p className="model-answer">{result.answer}</p>
          <button className="copy-button" type="button" onClick={copy}>
            {copied ? <Check size={15} /> : <Clipboard size={15} />}{" "}
            {copied ? "복사됨" : "답변 복사"}
          </button>
        </>
      ) : (
        <p className="model-error" role="alert">
          {result.error}
        </p>
      )}
      <dl className="model-metrics">
        <div>
          <dt>응답 시간</dt>
          <dd>{result.responseTimeSeconds.toFixed(2)} sec</dd>
        </div>
        <div>
          <dt>입력 / 출력</dt>
          <dd>
            {result.inputTokens} / {result.outputTokens} tokens
          </dd>
        </div>
        <div>
          <dt>설정</dt>
          <dd>
            {result.chunkSize} chunk · {result.overlap} overlap
          </dd>
        </div>
      </dl>
    </article>
  );
}
