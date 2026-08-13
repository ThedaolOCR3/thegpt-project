export type ModelTier = 'recommended' | 'beta';

export type ModelOption = {
  id: string;
  label: string;
  tier: ModelTier;
};

// 실제로는 백엔드에 붙는 provider 목록과 동일하게 맞춰야 한다 (지금은 UI만 있는 mock).
// 메인으로 쓸 모델 하나만 recommended로 두고, 나머지는 전부 beta로 표기한다.
export const MODEL_OPTIONS: ModelOption[] = [
  { id: 'medgemma', label: 'medgemma', tier: 'recommended' },
  { id: 'gemma', label: 'gemma', tier: 'beta' },
  { id: 'qwen', label: 'Qwen', tier: 'beta' },
  { id: 'llama', label: 'Llama', tier: 'beta' },
];

export function getModelOption(id: string): ModelOption {
  return MODEL_OPTIONS.find((option) => option.id === id) ?? MODEL_OPTIONS[0];
}
