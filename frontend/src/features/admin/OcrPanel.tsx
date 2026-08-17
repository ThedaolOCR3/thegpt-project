import { useRef, useState, type DragEvent } from 'react';
import { Check, FileText, RefreshCw, Trash2, UploadCloud } from 'lucide-react';
import { analyzeDocumentMock } from './adminMockApi';
import type { OcrDocumentResult } from './types';

const ACCEPTED_TYPES = '.pdf,.png,.jpg,.jpeg';

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function OcrPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<OcrDocumentResult | null>(null);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  function selectFile(nextFile?: File) {
    if (!nextFile) return;
    setFile(nextFile);
    setResult(null);
    setError('');
    setSaveMessage('');
  }

  function removeFile() {
    setFile(null);
    setResult(null);
    setError('');
    setSaveMessage('');
    if (inputRef.current) inputRef.current.value = '';
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  async function analyze() {
    if (!file || isAnalyzing) return;
    setIsAnalyzing(true);
    setResult(null);
    setError('');
    setSaveMessage('');
    try {
      setResult(await analyzeDocumentMock({ file }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '문서 분석 테스트에 실패했습니다.');
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <section className="admin-workspace" aria-labelledby="ocr-panel-title">
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">RAG DOCUMENT LAB</span>
          <h2 id="ocr-panel-title">문서 OCR 준비 테스트</h2>
          <p>문서가 RAG 지식으로 등록되기 전에 추출 품질과 예상 chunk 구성을 확인합니다.</p>
        </div>
        <span className="mock-badge">프론트엔드 Mock</span>
      </div>

      <div className="ocr-layout">
        <div className="admin-card ocr-input-card">
          <div
            className={`file-dropzone ${isDragging ? 'is-dragging' : ''}`}
            onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <UploadCloud aria-hidden="true" size={32} />
            <strong>문서를 끌어 놓거나 직접 선택하세요</strong>
            <span>PDF, PNG, JPG · 실제 파일 내용은 읽거나 전송하지 않습니다.</span>
            <button className="admin-secondary-button" type="button" onClick={() => inputRef.current?.click()}>
              파일 선택
            </button>
            <input
              ref={inputRef}
              className="admin-visually-hidden"
              type="file"
              accept={ACCEPTED_TYPES}
              aria-label="OCR 테스트 파일 선택"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />
          </div>

          {file ? (
            <div className="selected-file" aria-live="polite">
              <span className="file-icon"><FileText size={19} /></span>
              <div>
                <strong>{file.name}</strong>
                <span>{formatBytes(file.size)} · {file.type || '형식 정보 없음'}</span>
              </div>
              <button type="button" className="icon-button" onClick={removeFile} aria-label="선택 파일 제거">
                <Trash2 size={17} />
              </button>
            </div>
          ) : (
            <div className="admin-empty-inline">아직 선택한 문서가 없습니다.</div>
          )}

          {error && <p className="admin-error" role="alert">{error}</p>}
          <button
            className="admin-primary-button"
            type="button"
            disabled={!file || isAnalyzing}
            onClick={analyze}
          >
            {isAnalyzing ? <><RefreshCw className="spin" size={17} /> 분석 중...</> : '문서 분석 테스트'}
          </button>
        </div>

        <div className="admin-card ocr-result-card" aria-live="polite" aria-busy={isAnalyzing}>
          {isAnalyzing ? (
            <div className="admin-loading-state">
              <span className="loading-orbit" />
              <strong>OCR 결과를 준비하고 있습니다</strong>
              <p>고정 fixture로 추출 품질과 chunk 결과를 생성합니다.</p>
            </div>
          ) : result ? (
            <OcrResult
              result={result}
              saveMessage={saveMessage}
              onSave={() => setSaveMessage('저장 테스트가 완료되었습니다. 실제 VectorDB에는 저장되지 않았습니다.')}
            />
          ) : (
            <div className="admin-empty-state">
              <FileText size={34} />
              <strong>분석 결과가 여기에 표시됩니다</strong>
              <p>문서를 선택하고 분석 테스트를 실행해 주세요.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function OcrResult({
  result,
  saveMessage,
  onSave,
}: {
  result: OcrDocumentResult;
  saveMessage: string;
  onSave: () => void;
}) {
  return (
    <div className="ocr-result">
      <div className="result-title-row">
        <div><span>분석 완료</span><h3>{result.documentName}</h3></div>
        <span className={`readiness-badge ${result.readiness}`}>
          <Check size={13} /> {result.readiness === 'ready' ? '등록 가능' : '검토 필요'}
        </span>
      </div>
      <dl className="metric-grid">
        <div><dt>페이지</dt><dd>{result.pageCount}</dd></div>
        <div><dt>추출 문자</dt><dd>{result.characterCount.toLocaleString()}</dd></div>
        <div><dt>예상 Chunk</dt><dd>{result.estimatedChunks}</dd></div>
        <div><dt>인식 신뢰도</dt><dd>{result.confidence}%</dd></div>
      </dl>
      <div className="result-block">
        <h4>추출 텍스트 미리보기</h4>
        <p>{result.extractedText}</p>
      </div>
      <div className="result-block">
        <h4>Chunked Text</h4>
        <div className="chunk-list">
          {result.chunks.map((chunk) => <p key={chunk}>{chunk}</p>)}
        </div>
      </div>
      <div className="quality-note">
        <strong>품질 확인 메모</strong>
        <ul>{result.notes.map((note) => <li key={note}>{note}</li>)}</ul>
      </div>
      <button className="admin-primary-button" type="button" onClick={onSave} disabled={Boolean(saveMessage)}>
        {saveMessage ? '저장 테스트 완료' : 'VectorDB 저장 테스트'}
      </button>
      {saveMessage && <p className="admin-success" role="status">{saveMessage}</p>}
    </div>
  );
}
