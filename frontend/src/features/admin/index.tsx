import { useRef, useState, type KeyboardEvent } from 'react';
import { BrainCircuit, ScanText } from 'lucide-react';
import { LlmPanel } from './LlmPanel';
import { OcrPanel } from './OcrPanel';
import type { AdminTab } from './types';
import './admin.css';

const TABS: { id: AdminTab; label: string }[] = [
  { id: 'ocr', label: 'OCR' },
  { id: 'llm', label: 'LLM' },
];

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('ocr');
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % TABS.length;
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + TABS.length) % TABS.length;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = TABS.length - 1;
    setActiveTab(TABS[nextIndex].id);
    tabRefs.current[nextIndex]?.focus();
  }

  return (
    <div className="admin-page">
      <header className="admin-hero">
        <div className="admin-hero-icon" aria-hidden="true"><BrainCircuit size={27} /></div>
        <div>
          <span className="admin-eyebrow">ADMIN EXPERIMENT SPACE</span>
          <h1>AI 관리 도구</h1>
          <p>RAG 문서 준비 상태를 시험하고 여러 LLM의 응답을 같은 조건에서 비교합니다.</p>
        </div>
      </header>

      <div className="admin-tabs" role="tablist" aria-label="AI 관리 도구">
        {TABS.map((tab, index) => (
          <button
            key={tab.id}
            ref={(element) => { tabRefs.current[index] = element; }}
            id={`${tab.id}-tab`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`${tab.id}-tabpanel`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            className={activeTab === tab.id ? 'active' : ''}
            onClick={() => setActiveTab(tab.id)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
          >
            {tab.id === 'ocr' ? <ScanText size={17} /> : <BrainCircuit size={17} />}
            {tab.label}
          </button>
        ))}
      </div>

      <div
        id={`${activeTab}-tabpanel`}
        role="tabpanel"
        aria-labelledby={`${activeTab}-tab`}
        className="admin-tabpanel"
      >
        {activeTab === 'ocr' ? <OcrPanel /> : <LlmPanel />}
      </div>
    </div>
  );
}

