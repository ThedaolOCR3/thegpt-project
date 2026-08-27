import { useRef, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { runRetrievalEvaluation } from "../../../../api/evaluations";
import type { RetrievalEvalResult } from "../../../../api/evaluations";
import { ApiError } from "../../../../services/apiClient";

export function EvaluationPanel() {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<RetrievalEvalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function runEvaluation() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("loading");
    setError(null);
    try {
      const data = await runRetrievalEvaluation(controller.signal);
      setResult(data);
      setStatus("success");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof ApiError ? err.message : "평가 실행에 실패했어요.");
      setStatus("error");
    }
  }

  const kValues = result ? Object.keys(result.recallAtK).sort((a, b) => Number(a) - Number(b)) : [];

  return (
    <section className="admin-workspace" aria-labelledby="eval-panel-title">
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">RAG RETRIEVAL EVAL</span>
          <h2 id="eval-panel-title">검색 정확도 (Recall@k / MRR)</h2>
          <p>
            미리 준비된 평가 데이터셋(<code>scripts/eval_data</code>)에 대해 검색
            정확도를 계산합니다. 임베딩 모델이 아직 확정 전이라 지금은 자리 채우기용
            해싱 임베딩 기준 수치입니다 — 의미 기반 검색 품질은 없고, 실제 모델이
            연결되면 이 숫자보다 훨씬 좋아져야 정상입니다.
          </p>
        </div>
      </div>

      <p className="llm-provider-notice">
        corpus/쿼리 임베딩을 매번 새로 계산합니다(캐시 없음). 지금은 해싱 임베딩이라
        1초 안에 끝나지만, 실제 임베딩 모델로 교체되면 데이터셋 크기에 따라
        <strong> 몇 분 정도</strong> 걸릴 수 있습니다. 하이브리드 검색(BM25/reranker)이
        아니라 dense 임베딩 단독 기준 지표입니다.
      </p>

      <button
        type="button"
        className="admin-primary-button"
        onClick={() => void runEvaluation()}
        disabled={status === "loading"}
      >
        {status === "loading" ? (
          <>
            <Loader2 className="spin" size={16} /> 평가 실행 중... (몇 분 걸릴 수 있어요)
          </>
        ) : (
          <>
            <RefreshCw size={16} /> 평가 실행
          </>
        )}
      </button>

      {status === "error" && (
        <p className="admin-error" role="alert">
          {error}
        </p>
      )}

      {result && (
        <div className="admin-card" style={{ marginTop: "1rem" }}>
          <div className="admin-card-header">
            <span>{result.datasetName}</span>
            <span className="mock-badge">쿼리 {result.numQueries}개</span>
          </div>
          <table className="admin-eval-table">
            <thead>
              <tr>
                {kValues.map((k) => (
                  <th key={k}>Recall@{k}</th>
                ))}
                <th>MRR</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                {kValues.map((k) => (
                  <td key={k}>{(result.recallAtK[k] * 100).toFixed(1)}%</td>
                ))}
                <td>{result.mrr.toFixed(3)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
