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
            같은 질문과 동일한 참고 문서 조건에서 학습 단계와 모델 종류에 따른
            응답 품질 및 실행 지표를 비교합니다.
          </p>
        </div>
        <span className="mock-badge">Backend Mock</span>
      </div>

      <LlmTestForm
        prompt={llm.prompt}
        file={llm.file}
        isRunningAll={llm.isRunningAll}
        hasRunningModels={llm.hasRunningModels}
        error={llm.error}
        onPromptChange={llm.setPrompt}
        onFileChange={llm.setFile}
        onRunAll={() => void llm.runAllModels()}
        onReset={llm.reset}
      />

      <LlmResultGrid
        modelRuns={llm.modelRuns}
        onRunModel={(modelId) => void llm.runModel(modelId)}
        onCancelModel={llm.cancelModel}
      />
    </section>
  );
}
