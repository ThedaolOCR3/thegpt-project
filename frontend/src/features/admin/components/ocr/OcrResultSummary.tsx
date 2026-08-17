import { Check, FileText } from 'lucide-react';
import type { AsyncStatus } from '../../types/common';
import type { OcrDocumentResult } from '../../types/ocr';

export function OcrResultSummary({ status, result, saveStatus, saveMessage, onSave }: { status: AsyncStatus; result: OcrDocumentResult | null; saveStatus: AsyncStatus; saveMessage: string; onSave: () => void }) {
  if (status === 'loading') return <div className="admin-loading-state"><span className="loading-orbit" /><strong>OCR 결과를 준비하고 있습니다</strong><p>고정 fixture로 추출 품질과 chunk 결과를 생성합니다.</p></div>;
  if (!result) return <div className="admin-empty-state"><FileText size={34} /><strong>분석 결과가 여기에 표시됩니다</strong><p>문서를 선택하고 분석 테스트를 실행해 주세요.</p></div>;
  return <div className="ocr-result">
    <div className="result-title-row"><div><span>분석 완료</span><h3>{result.documentName}</h3></div><span className={`readiness-badge ${result.readiness}`}><Check size={13} /> {result.readiness === 'ready' ? '등록 가능' : '검토 필요'}</span></div>
    <dl className="metric-grid"><div><dt>페이지</dt><dd>{result.pageCount}</dd></div><div><dt>추출 문자</dt><dd>{result.characterCount.toLocaleString()}</dd></div><div><dt>예상 Chunk</dt><dd>{result.estimatedChunks}</dd></div><div><dt>인식 신뢰도</dt><dd>{result.confidence}%</dd></div></dl>
    <TextPreview title="추출 텍스트 미리보기" texts={[result.extractedText]} />
    <TextPreview title="Chunked Text" texts={result.chunks} chunked />
    <div className="quality-note"><strong>품질 확인 메모</strong><ul>{result.notes.map((note) => <li key={note}>{note}</li>)}</ul></div>
    <button className="admin-primary-button" type="button" onClick={onSave} disabled={saveStatus === 'loading' || saveStatus === 'success'}>{saveStatus === 'loading' ? '저장 테스트 중...' : saveStatus === 'success' ? '저장 테스트 완료' : 'VectorDB 저장 테스트'}</button>
    {saveMessage && <p className={saveStatus === 'error' ? 'admin-error' : 'admin-success'} role="status">{saveMessage}</p>}
  </div>;
}

function TextPreview({ title, texts, chunked = false }: { title: string; texts: string[]; chunked?: boolean }) {
  return <div className="result-block"><h4>{title}</h4>{chunked ? <div className="chunk-list">{texts.map((text) => <p key={text}>{text}</p>)}</div> : <p>{texts[0]}</p>}</div>;
}
