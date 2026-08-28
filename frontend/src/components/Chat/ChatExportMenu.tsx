import { useState } from 'react';
import { Download } from 'lucide-react';
import type { Message } from '../../api/types';
import {
  buildFilenameBase,
  buildTranscriptMarkdown,
  buildTranscriptText,
  downloadTextFile,
  openPrintableTranscript,
  type ExportMode,
} from '../../utils/chatExport';

type ChatExportMenuProps = {
  messages: Message[];
  title: string;
};

type Format = 'txt' | 'md' | 'pdf';

// 채팅내역을 파일로 저장하는 버튼 + 팝오버.
// - 전체 저장: 원문 그대로 (병원 제출처럼 정확성이 중요한 용도에 권장)
// - 요약 저장: 환자 메시지는 원문 유지, AI 답변만 첫 문장으로 발췌해 짧게 훑어볼 때 씀
//   (LLM 재요약은 하지 않음 — chatExport.ts의 firstSentence 주석 참고)
export function ChatExportMenu({ messages, title }: ChatExportMenuProps) {
  const [open, setOpen] = useState(false);

  function handleExport(mode: ExportMode, format: Format) {
    if (messages.length === 0) {
      window.alert('저장할 대화 내용이 없어요.');
      return;
    }
    const filenameBase = buildFilenameBase(messages, mode);
    if (format === 'txt') {
      downloadTextFile(`${filenameBase}.txt`, buildTranscriptText(title, messages, mode), 'text/plain');
    } else if (format === 'md') {
      downloadTextFile(`${filenameBase}.md`, buildTranscriptMarkdown(title, messages, mode), 'text/markdown');
    } else {
      openPrintableTranscript(title, messages, mode);
    }
    setOpen(false);
  }

  return (
    <div className="relative">
      <button
        type="button"
        title="채팅내역 저장"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
      >
        <Download size={14} />
        채팅내역 저장
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full z-20 mt-1 w-64 rounded-xl border border-neutral-200 bg-white p-2 shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
            <ExportSection
              label="전체 저장"
              description="대화 원문 그대로 (병원 제출용으로 추천)"
              mode="full"
              onPick={handleExport}
            />
            <div className="my-2 border-t border-neutral-100 dark:border-neutral-800" />
            <ExportSection
              label="요약 저장"
              description="AI 답변은 첫 문장만 발췌, 환자 메시지는 원문 유지"
              mode="summary"
              onPick={handleExport}
            />
          </div>
        </>
      )}
    </div>
  );
}

function ExportSection({
  label,
  description,
  mode,
  onPick,
}: {
  label: string;
  description: string;
  mode: ExportMode;
  onPick: (mode: ExportMode, format: Format) => void;
}) {
  return (
    <div className="px-1 py-1">
      <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-200">{label}</p>
      <p className="mb-1.5 text-[11px] text-neutral-400">{description}</p>
      <div className="flex gap-1.5">
        {(['txt', 'md', 'pdf'] as Format[]).map((format) => (
          <button
            key={format}
            type="button"
            onClick={() => onPick(mode, format)}
            className="flex-1 rounded-lg border border-neutral-200 py-1 text-[11px] font-medium uppercase text-neutral-500 hover:border-blue-400 hover:text-blue-600 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-blue-500 dark:hover:text-blue-400"
          >
            {format}
          </button>
        ))}
      </div>
    </div>
  );
}
