import { createContext, useContext, useState, type ReactNode } from 'react';
import { MODEL_OPTIONS } from './modelOptions';

type ModelSelectContextValue = {
  modelId: string;
  setModelId: (id: string) => void;
};

const ModelSelectContext = createContext<ModelSelectContextValue | null>(null);
const STORAGE_KEY = 'thegpt-selected-model';

function getInitialModelId() {
  return localStorage.getItem(STORAGE_KEY) ?? MODEL_OPTIONS[0].id;
}

// 홈 화면에서 고른 모델이 채팅 화면으로 넘어가도 유지되도록 컨텍스트로 공유한다.
// 지금은 mock이라 어떤 모델을 골라도 응답은 동일하다 — 실제 라우팅은 백엔드 연동 후 적용.
export function ModelSelectProvider({ children }: { children: ReactNode }) {
  const [modelId, setModelIdState] = useState(getInitialModelId);

  function setModelId(id: string) {
    setModelIdState(id);
    localStorage.setItem(STORAGE_KEY, id);
  }

  return (
    <ModelSelectContext.Provider value={{ modelId, setModelId }}>{children}</ModelSelectContext.Provider>
  );
}

export function useModelSelect() {
  const context = useContext(ModelSelectContext);
  if (!context) throw new Error('useModelSelect는 ModelSelectProvider 안에서만 사용할 수 있습니다.');
  return context;
}
