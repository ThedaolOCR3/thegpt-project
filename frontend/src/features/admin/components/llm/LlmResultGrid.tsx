import {
  MAIN_LLM_COMPARISON_MODELS,
  OTHER_LLM_COMPARISON_MODELS,
} from "../../constants/adminOptions";
import type {
  LlmModelDefinition,
  LlmModelRunMap,
} from "../../types/llm";
import { LlmResultCard } from "./LlmResultCard";

type Props = {
  modelRuns: LlmModelRunMap;
  onRunModel: (modelId: string) => void;
  onCancelModel: (modelId: string) => void;
};

function ModelGroup({
  models,
  className,
  modelRuns,
  onRunModel,
  onCancelModel,
}: Props & {
  models: readonly LlmModelDefinition[];
  className: string;
}) {
  return (
    <div className={className}>
      {models.map((model) => (
        <LlmResultCard
          key={model.id}
          model={model}
          run={modelRuns[model.id]}
          onRun={() => onRunModel(model.id)}
          onCancel={() => onCancelModel(model.id)}
        />
      ))}
    </div>
  );
}

export function LlmResultGrid(props: Props) {
  const isBusy = Object.values(props.modelRuns).some(
    (run) => run.status === "running",
  );

  return (
    <div
      className="llm-comparison-results"
      aria-busy={isBusy}
    >
      <section
        className="llm-comparison-section"
        aria-labelledby="main-model-comparison-title"
      >
        <div className="llm-group-heading">
          <span>TRAINING STAGE</span>
          <h3 id="main-model-comparison-title">메인 모델 학습 단계 비교</h3>
          <p>
            학습과 파인튜닝을 완료한 모델과 동일 계열의 부분 학습 모델을
            비교합니다.
          </p>
        </div>
        <ModelGroup
          {...props}
          models={MAIN_LLM_COMPARISON_MODELS}
          className="llm-model-grid main-model-grid"
        />
      </section>

      <section
        className="llm-comparison-section"
        aria-labelledby="other-model-comparison-title"
      >
        <div className="llm-group-heading">
          <span>MODEL FAMILY</span>
          <h3 id="other-model-comparison-title">다른 LLM 비교</h3>
          <p>
            동일한 질문을 다른 종류의 Mock LLM에 전달해 응답 내용과 실행
            성능을 비교합니다.
          </p>
        </div>
        <ModelGroup
          {...props}
          models={OTHER_LLM_COMPARISON_MODELS}
          className="llm-model-grid other-model-grid"
        />
      </section>
    </div>
  );
}
