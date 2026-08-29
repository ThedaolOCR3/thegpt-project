export type ModelTier = 'recommended' | 'beta';

export type ModelOption = {
  id: string;
  label: string;
  tier: ModelTier;
};

// Backend의 Vast.ai 원격 모델 Registry와 동일한 ID를 사용한다.
// 메인으로 쓸 모델 하나만 recommended로 두고, 나머지는 전부 beta로 표기한다.
export const MODEL_OPTIONS: ModelOption[] = [
  { id: 'medgemma', label: 'MedGemma 최종', tier: 'recommended' },
  { id: 'medgemma-dataset', label: 'MedGemma 데이터셋', tier: 'beta' },
  { id: 'gemma', label: 'Gemma Medical', tier: 'beta' },
  { id: 'qwen', label: 'Qwen', tier: 'beta' },
  { id: 'llama', label: 'Llama', tier: 'beta' },
];

export function getModelOption(id: string): ModelOption {
  return MODEL_OPTIONS.find((option) => option.id === id) ?? MODEL_OPTIONS[0];
}
