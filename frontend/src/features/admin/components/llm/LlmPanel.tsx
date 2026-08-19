import { useLlmComparison } from "../../hooks/useLlmComparison";
import { LlmResultGrid } from "./LlmResultGrid";
import { LlmTestForm } from "./LlmTestForm";

export function LlmPanel() {
  const llm = useLlmComparison();
  return (
    <section className="admin-workspace" aria-labelledby="llm-panel-title">
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">MODEL COMPARISON LAB</span>
          <h2 id="llm-panel-title">LLM 응답 비교</h2>
          <p>
            같은 질문과 RAG 옵션으로 여러 모델의 답변 형식과 지표를 나란히
            비교합니다.
          </p>
        </div>
        {/* <span className="mock-badge">프론트엔드 Mock</span> */}
      </div>
      <LlmTestForm
        prompt={llm.prompt}
        modelIds={llm.modelIds}
        file={llm.file}
        chunkSize={llm.chunkSize}
        overlap={llm.overlap}
        status={llm.status}
        error={llm.error}
        onPromptChange={llm.setPrompt}
        onToggleModel={llm.toggleModel}
        onFileChange={llm.setFile}
        onChunkSizeChange={llm.setChunkSize}
        onOverlapChange={llm.setOverlap}
        onCompare={llm.compare}
        onReset={llm.reset}
      />
      <LlmResultGrid
        status={llm.status}
        modelIds={llm.modelIds}
        results={llm.results}
      />
    </section>
  );
}
