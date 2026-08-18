import type { AsyncStatus } from "../../types/common";
import type { LlmComparisonResult } from "../../types/llm";
import { LlmResultCard, LoadingModelCard } from "./LlmResultCard";

export function LlmResultGrid({
  status,
  modelIds,
  results,
}: {
  status: AsyncStatus;
  modelIds: string[];
  results: LlmComparisonResult[];
}) {
  return (
    <div
      className="llm-results"
      aria-live="polite"
      aria-busy={status === "loading"}
    >
      {status === "loading" ? (
        modelIds.map((id) => <LoadingModelCard key={id} modelId={id} />)
      ) : results.length ? (
        results.map((result) => (
          <LlmResultCard key={result.modelId} result={result} />
        ))
      ) : (
        <div className="admin-card admin-empty-state llm-empty">
          <strong>비교 결과가 아직 없습니다</strong>
          <p>질문과 모델을 선택한 뒤 비교를 실행해 주세요.</p>
        </div>
      )}
    </div>
  );
}
