import { useRef, useState } from 'react';
import { Check, Clipboard, FileText, LoaderCircle, RotateCcw, X } from 'lucide-react';
import { MODEL_OPTIONS, getModelOption } from '../../components/Chat/modelOptions';
import { compareModelsMock } from './adminMockApi';
import type { LlmComparisonResult } from './types';

const DEFAULT_MODELS = ['medgemma', 'gemma', 'qwen'];

export function LlmPanel() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>(DEFAULT_MODELS);
  const [file, setFile] = useState<File | null>(null);
  const [chunkSize, setChunkSize] = useState(512);
  const [overlap, setOverlap] = useState(50);
  const [results, setResults] = useState<LlmComparisonResult[]>([]);
  const [error, setError] = useState('');
  const [isComparing, setIsComparing] = useState(false);

  function toggleModel(modelId: string) {
    setSelectedModels((current) => current.includes(modelId)
      ? current.filter((id) => id !== modelId)
      : [...current, modelId]);
  }

  function validate() {
    if (!prompt.trim()) return '비교할 공통 질문을 입력해 주세요.';
    if (selectedModels.length < 2) return '비교할 모델을 2개 이상 선택해 주세요.';
    if (chunkSize < 100 || chunkSize > 4096) return 'Chunk Size는 100~4096 사이로 입력해 주세요.';
    if (overlap < 0 || overlap >= chunkSize) return 'Overlap은 0 이상이며 Chunk Size보다 작아야 합니다.';
    return '';
  }

  async function compare() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError('');
    setResults([]);
    setIsComparing(true);
    try {
      setResults(await compareModelsMock({
        prompt: prompt.trim(),
        modelIds: selectedModels,
        file: file ?? undefined,
        chunkSize,
        overlap,
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '모델 비교 테스트에 실패했습니다.');
    } finally {
      setIsComparing(false);
    }
  }

  function reset() {
    setPrompt('');
    setSelectedModels(DEFAULT_MODELS);
    setFile(null);
    setChunkSize(512);
    setOverlap(50);
    setResults([]);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  return (
    <section className="admin-workspace" aria-labelledby="llm-panel-title">
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">MODEL COMPARISON LAB</span>
          <h2 id="llm-panel-title">LLM 응답 비교</h2>
          <p>같은 질문과 RAG 옵션으로 여러 모델의 답변 형식과 지표를 나란히 비교합니다.</p>
        </div>
        <span className="mock-badge">프론트엔드 Mock</span>
      </div>

      <div className="admin-card llm-form-card">
        <label className="admin-field">
          <span>공통 질문 또는 Prompt</span>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="예: 이 의료 문서의 핵심 내용을 근거 중심으로 요약해 주세요."
            rows={4}
          />
        </label>

        <div className="llm-attachment-row">
          <button className="admin-secondary-button" type="button" onClick={() => fileInputRef.current?.click()}>
            <FileText size={16} /> 참고 문서 선택
          </button>
          <input
            ref={fileInputRef}
            className="admin-visually-hidden"
            type="file"
            aria-label="LLM 비교 참고 문서 선택"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          {file && (
            <span className="file-chip">
              {file.name}
              <button type="button" aria-label="참고 문서 제거" onClick={() => setFile(null)}><X size={13} /></button>
            </span>
          )}
          <small>파일명만 요청 상태에 포함되며 파일은 읽거나 업로드하지 않습니다.</small>
        </div>

        <fieldset className="model-fieldset">
          <legend>비교 모델 <span>2개 이상 선택</span></legend>
          <div className="model-choice-grid">
            {MODEL_OPTIONS.map((model) => (
              <label className={`model-choice ${selectedModels.includes(model.id) ? 'selected' : ''}`} key={model.id}>
                <input
                  type="checkbox"
                  checked={selectedModels.includes(model.id)}
                  onChange={() => toggleModel(model.id)}
                />
                <span>{model.label}</span>
                <small>{model.id === 'llama' ? '부분 오류 fixture' : model.tier}</small>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="llm-options">
          <label className="admin-field">
            <span>Chunk Size</span>
            <input type="number" min={100} max={4096} value={chunkSize} onChange={(event) => setChunkSize(Number(event.target.value))} />
          </label>
          <label className="admin-field">
            <span>Overlap</span>
            <input type="number" min={0} value={overlap} onChange={(event) => setOverlap(Number(event.target.value))} />
          </label>
        </div>

        {error && <p className="admin-error" role="alert">{error}</p>}
        <div className="admin-form-actions">
          <button className="admin-secondary-button" type="button" onClick={reset} disabled={isComparing}>
            <RotateCcw size={16} /> 입력 초기화
          </button>
          <button className="admin-primary-button" type="button" onClick={compare} disabled={isComparing}>
            {isComparing ? <><LoaderCircle className="spin" size={17} /> 비교 생성 중...</> : '모델 응답 비교'}
          </button>
        </div>
      </div>

      <div className="llm-results" aria-live="polite" aria-busy={isComparing}>
        {isComparing ? selectedModels.map((modelId) => <LoadingModelCard key={modelId} modelId={modelId} />)
          : results.length > 0 ? results.map((result) => <LlmResultCard key={result.modelId} result={result} />)
            : <div className="admin-card admin-empty-state llm-empty"><strong>비교 결과가 아직 없습니다</strong><p>질문과 모델을 선택한 뒤 비교를 실행해 주세요.</p></div>}
      </div>
    </section>
  );
}

function LoadingModelCard({ modelId }: { modelId: string }) {
  return (
    <article className="admin-card model-result-card loading-card">
      <div className="model-card-header"><h3>{getModelOption(modelId).label}</h3><span><LoaderCircle className="spin" size={14} /> 생성 중</span></div>
      <div className="skeleton-line wide" /><div className="skeleton-line" /><div className="skeleton-line short" />
    </article>
  );
}

function LlmResultCard({ result }: { result: LlmComparisonResult }) {
  const [copied, setCopied] = useState(false);
  const model = getModelOption(result.modelId);

  async function copyAnswer() {
    if (!result.answer) return;
    await navigator.clipboard.writeText(result.answer);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <article className={`admin-card model-result-card ${result.status}`}>
      <div className="model-card-header">
        <div><span>{model.tier}</span><h3>{model.label}</h3></div>
        <span className={`model-status ${result.status}`}>
          {result.status === 'success' ? <Check size={13} /> : <X size={13} />}
          {result.status === 'success' ? '성공' : '오류'}
        </span>
      </div>
      {result.status === 'success' ? (
        <>
          <p className="model-answer">{result.answer}</p>
          <button className="copy-button" type="button" onClick={copyAnswer}>
            {copied ? <Check size={15} /> : <Clipboard size={15} />} {copied ? '복사됨' : '답변 복사'}
          </button>
        </>
      ) : <p className="model-error" role="alert">{result.error}</p>}
      <dl className="model-metrics">
        <div><dt>응답 시간</dt><dd>{result.responseTimeSeconds.toFixed(2)} sec</dd></div>
        <div><dt>입력 / 출력</dt><dd>{result.inputTokens} / {result.outputTokens} tokens</dd></div>
        <div><dt>설정</dt><dd>{result.chunkSize} chunk · {result.overlap} overlap</dd></div>
      </dl>
    </article>
  );
}
