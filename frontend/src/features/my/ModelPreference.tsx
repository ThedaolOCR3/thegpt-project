import { useModelSelect } from '../../components/Chat/ModelSelectContext';
import { MODEL_OPTIONS } from '../../components/Chat/modelOptions';

export function ModelPreference() {
  const { modelId, setModelId } = useModelSelect();
  return <label className="setting-field">기본 AI 모델
    <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
      {MODEL_OPTIONS.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
    </select>
  </label>;
}
