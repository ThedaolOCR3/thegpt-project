import { useState } from 'react';
import { X } from 'lucide-react';

type DocumentPreviewPanelProps = {
  fileName: string;
  onClose: () => void;
};

// 원본 문서 vs 파싱된 텍스트를 나란히 보여주는 우측 패널.
// 백엔드/OCR 연동 전까지는 mock 텍스트를 보여주고, 사용자가 직접 수정만 가능하게 한다.
// 실제 연동 시에는 파싱된 텍스트를 이 컴포넌트의 props로 주입하고, onSave 콜백으로
// 수정 결과를 백엔드에 반영하면 된다.
export function DocumentPreviewPanel({ fileName, onClose }: DocumentPreviewPanelProps) {
  const [parsedText, setParsedText] = useState(
    `[Mock] "${fileName}"에서 추출된 텍스트입니다.\n\n실제 OCR/문서 파싱이 연동되면 이 영역에 진짜 추출 결과가 표시되고,\n아래에서 직접 수정할 수 있습니다.`,
  );

  return (
    <aside className="flex h-full w-96 shrink-0 flex-col border-l border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900">
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
        <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-100">{fileName}</p>
        <button
          type="button"
          title="미리보기 닫기"
          onClick={onClose}
          className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <p className="mb-1.5 text-xs font-semibold text-neutral-400">원본 문서</p>
        <div className="mb-4 flex h-40 items-center justify-center rounded-lg border border-dashed border-neutral-300 text-xs text-neutral-400 dark:border-neutral-600">
          원본 미리보기 (연동 전 mock)
        </div>

        <p className="mb-1.5 text-xs font-semibold text-neutral-400">파싱된 텍스트 (수정 가능)</p>
        <textarea
          value={parsedText}
          onChange={(e) => setParsedText(e.target.value)}
          rows={10}
          className="w-full resize-none rounded-lg border border-neutral-200 p-2.5 text-sm text-neutral-800 focus:border-blue-400 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        />
      </div>
    </aside>
  );
}
