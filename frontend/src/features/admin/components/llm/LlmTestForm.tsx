import { useRef } from 'react';
import { FileText, LoaderCircle, RotateCcw, X } from 'lucide-react';
import { MODEL_OPTIONS } from '../../../../components/Chat/modelOptions';
import type { AsyncStatus } from '../../types/common';

type Props = {
  prompt: string; modelIds: string[]; file: File | null; chunkSize: number; overlap: number;
  status: AsyncStatus; error: string;
  onPromptChange: (value: string) => void; onToggleModel: (id: string) => void;
  onFileChange: (file: File | null) => void; onChunkSizeChange: (value: number) => void;
  onOverlapChange: (value: number) => void; onCompare: () => void; onReset: () => void;
};

export function LlmTestForm(props: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const loading = props.status === 'loading';
  return <div className="admin-card llm-form-card">
    <label className="admin-field"><span>공통 질문 또는 Prompt</span><textarea value={props.prompt} onChange={(event) => props.onPromptChange(event.target.value)} placeholder="예: 이 의료 문서의 핵심 내용을 근거 중심으로 요약해 주세요." rows={4} disabled={loading} /></label>
    <div className="llm-attachment-row"><button className="admin-secondary-button" type="button" disabled={loading} onClick={() => fileRef.current?.click()}><FileText size={16} /> 참고 문서 선택</button>
      <input ref={fileRef} className="admin-visually-hidden" type="file" aria-label="LLM 비교 참고 문서 선택" disabled={loading} onChange={(event) => props.onFileChange(event.target.files?.[0] ?? null)} />
      {props.file && <span className="file-chip">{props.file.name}<button type="button" aria-label="참고 문서 제거" onClick={() => { props.onFileChange(null); if (fileRef.current) fileRef.current.value = ''; }}><X size={13} /></button></span>}
      <small>파일명만 요청 상태에 포함되며 파일은 읽거나 업로드하지 않습니다.</small>
    </div>
    <fieldset className="model-fieldset" disabled={loading}><legend>비교 모델 <span>2개 이상 선택</span></legend><div className="model-choice-grid">{MODEL_OPTIONS.map((model) => <label className={`model-choice ${props.modelIds.includes(model.id) ? 'selected' : ''}`} key={model.id}><input type="checkbox" checked={props.modelIds.includes(model.id)} onChange={() => props.onToggleModel(model.id)} /><span>{model.label}</span><small>{model.id === 'llama' ? '부분 오류 fixture' : model.tier}</small></label>)}</div></fieldset>
    <div className="llm-options"><label className="admin-field"><span>Chunk Size</span><input type="number" min={100} max={4096} value={props.chunkSize} disabled={loading} onChange={(event) => props.onChunkSizeChange(Number(event.target.value))} /></label><label className="admin-field"><span>Overlap</span><input type="number" min={0} value={props.overlap} disabled={loading} onChange={(event) => props.onOverlapChange(Number(event.target.value))} /></label></div>
    {props.error && <p className="admin-error" role="alert">{props.error}</p>}
    <div className="admin-form-actions"><button className="admin-secondary-button" type="button" onClick={props.onReset} disabled={loading}><RotateCcw size={16} /> 입력 초기화</button><button className="admin-primary-button" type="button" onClick={props.onCompare} disabled={loading}>{loading ? <><LoaderCircle className="spin" size={17} /> 비교 생성 중...</> : '모델 응답 비교'}</button></div>
  </div>;
}
