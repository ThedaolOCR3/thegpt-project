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
// modelId는 그대로 api/messages.ts의 sendMessage()를 통해 백엔드로 전달된다.
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
