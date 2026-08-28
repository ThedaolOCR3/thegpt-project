export type ModelTier = 'recommended' | 'beta';

export type ModelOption = {
  id: string;
  label: string;
  tier: ModelTier;
  /** true면 선택은 가능하지만 지금은 실제로 응답을 못 준다(백엔드에 연결된 실제
   * 모델이 없음) — 선택 UI에서 이유를 보여줄 때 쓴다. */
  disconnected?: boolean;
};

// id는 ai/llm/registry.py의 LlmModelDefinition.id와 반드시 일치해야 한다 — 여기서
// 고른 값이 그대로 백엔드로 전달된다(api/messages.ts의 model_id).
// medgemma/qwen: 실제 의료 LoRA 어댑터 연결됨. llama: 어댑터는 등록됐지만 base
// model(meta-llama/Llama-3.2-3B-Instruct)이 HuggingFace Gated Repo라 Meta 라이선스
// 접근 승인 전까지는 항상 실패한다("준비만" 된 상태). gemma: 실제 의료 파인튜닝
// 모델이 아직 없어서 백엔드에 대응하는 model_id가 없다 — 고르면 안전하게 기본
// 모델(medgemma-main)로 대체된다(백엔드가 모르는 id를 던져도 채팅이 죽지 않음).
export const MODEL_OPTIONS: ModelOption[] = [
  { id: 'medgemma-main', label: 'MedGemma', tier: 'recommended' },
  { id: 'qwen-medical', label: 'Qwen3', tier: 'beta' },
  { id: 'llama-medical', label: 'Llama 3.2', tier: 'beta', disconnected: true },
  { id: 'gemma', label: 'Gemma', tier: 'beta', disconnected: true },
];

export function getModelOption(id: string): ModelOption {
  return MODEL_OPTIONS.find((option) => option.id === id) ?? MODEL_OPTIONS[0];
}
