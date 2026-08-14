import { useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, FileText, X } from 'lucide-react';
import type { MessageAttachment } from '../../api/types';

type DocumentPreviewPanelProps = {
  attachments: MessageAttachment[];
  index: number;
  onIndexChange: (index: number) => void;
  onClose: () => void;
};

const WIDTH_STORAGE_KEY = 'thegpt_preview_panel_width';
const MIN_WIDTH = 300;
const MAX_WIDTH = 760;
const DEFAULT_WIDTH = 384;

function isImage(attachment: MessageAttachment) {
  return attachment.type?.startsWith('image/') ?? /\.(png|jpe?g|gif|webp|bmp)$/i.test(attachment.name);
}

function isPdf(attachment: MessageAttachment) {
  return attachment.type === 'application/pdf' || /\.pdf$/i.test(attachment.name);
}

// 원본 문서 vs 파싱된 텍스트를 나란히 보여주는 우측 패널.
// - 원본: 방금 이 세션에서 첨부한 파일(blob: URL 있음)만 실제로 보여줄 수 있다.
//   서버는 아직 첨부파일 메타데이터만 저장하고 실제 바이트는 저장하지 않아서
//   (Object Storage 연동 전), 새로고침/이전 대화에서 불러온 첨부는 안내만 표시한다.
// - 파싱된 텍스트: OCR 연동 전까지는 mock. 연동되면 props로 실제 결과를 주입하면 된다.
// - 좌측 가장자리를 드래그해 폭을 조절할 수 있고(로컬에 기억), 첨부가 여러 개면
//   하단 썸네일 스트립 + 이전/다음 버튼으로 넘겨볼 수 있다.
export function DocumentPreviewPanel({ attachments, index, onIndexChange, onClose }: DocumentPreviewPanelProps) {
  const attachment = attachments[index];
  const [parsedText, setParsedText] = useState('');
  const [width, setWidth] = useState(() => {
    const stored = Number(localStorage.getItem(WIDTH_STORAGE_KEY));
    return stored >= MIN_WIDTH && stored <= MAX_WIDTH ? stored : DEFAULT_WIDTH;
  });
  const resizingRef = useRef(false);

  useEffect(() => {
    setParsedText(
      `[Mock] "${attachment?.name}"에서 추출된 텍스트입니다.\n\n실제 OCR/문서 파싱이 연동되면 이 영역에 진짜 추출 결과가 표시되고,\n아래에서 직접 수정할 수 있습니다.`,
    );
  }, [attachment?.name]);

  function startResize(event: React.MouseEvent) {
    event.preventDefault();
    resizingRef.current = true;
    document.body.style.cursor = 'col-resize';

    function handleMouseMove(moveEvent: MouseEvent) {
      if (!resizingRef.current) return;
      // 패널이 화면 우측에 붙어있으므로, 화면 오른쪽 끝에서 마우스 x좌표까지의 거리가 곧 폭.
      const next = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, window.innerWidth - moveEvent.clientX));
      setWidth(next);
    }
    function handleMouseUp() {
      resizingRef.current = false;
      document.body.style.cursor = '';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      setWidth((current) => {
        localStorage.setItem(WIDTH_STORAGE_KEY, String(current));
        return current;
      });
    }
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }

  if (!attachment) return null;

  return (
    <aside
      style={{ width }}
      className="relative flex h-full shrink-0 flex-col border-l border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900"
    >
      {/* 리사이즈 핸들 */}
      <div
        onMouseDown={startResize}
        title="드래그해서 폭 조절"
        className="absolute -left-1 top-0 h-full w-2 cursor-col-resize select-none"
      />

      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-100">{attachment.name}</p>
          {attachments.length > 1 && (
            <p className="text-xs text-neutral-400">
              {index + 1} / {attachments.length}
            </p>
          )}
        </div>
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
        <OriginalPreview attachment={attachment} />

        <p className="mb-1.5 mt-4 text-xs font-semibold text-neutral-400">파싱된 텍스트 (수정 가능)</p>
        <textarea
          value={parsedText}
          onChange={(e) => setParsedText(e.target.value)}
          rows={10}
          className="w-full resize-none rounded-lg border border-neutral-200 p-2.5 text-sm text-neutral-800 focus:border-blue-400 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
        />
      </div>

      {attachments.length > 1 && (
        <div className="flex items-center gap-1.5 border-t border-neutral-200 px-2 py-2 dark:border-neutral-700">
          <button
            type="button"
            title="이전 파일"
            aria-label="이전 파일"
            disabled={index === 0}
            onClick={() => onIndexChange(index - 1)}
            className="shrink-0 rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-neutral-800"
          >
            <ChevronLeft size={16} />
          </button>

          <div className="flex flex-1 gap-1.5 overflow-x-auto">
            {attachments.map((a, i) => (
              <button
                key={`${a.name}-${i}`}
                type="button"
                title={a.name}
                onClick={() => onIndexChange(i)}
                className={`flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg border text-neutral-400 ${
                  i === index
                    ? 'border-blue-500 ring-1 ring-blue-500'
                    : 'border-neutral-200 hover:border-neutral-300 dark:border-neutral-700'
                }`}
              >
                {isImage(a) && a.url ? (
                  <img src={a.url} alt={a.name} className="h-full w-full object-cover" />
                ) : (
                  <FileText size={16} />
                )}
              </button>
            ))}
          </div>

          <button
            type="button"
            title="다음 파일"
            aria-label="다음 파일"
            disabled={index === attachments.length - 1}
            onClick={() => onIndexChange(index + 1)}
            className="shrink-0 rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-neutral-800"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </aside>
  );
}

function OriginalPreview({ attachment }: { attachment: MessageAttachment }) {
  if (!attachment.url) {
    return (
      <div className="flex h-40 flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-neutral-300 px-3 text-center text-xs text-neutral-400 dark:border-neutral-600">
        <FileText size={20} />
        <p>원본이 아직 서버에 저장되지 않았어요.</p>
        <p>(방금 첨부한 파일만 이 세션에서 미리볼 수 있어요 — 스토리지 연동 전)</p>
      </div>
    );
  }

  if (isImage(attachment)) {
    return (
      <img
        src={attachment.url}
        alt={attachment.name}
        className="max-h-80 w-full rounded-lg border border-neutral-200 object-contain dark:border-neutral-700"
      />
    );
  }

  if (isPdf(attachment)) {
    return (
      <iframe
        src={attachment.url}
        title={attachment.name}
        className="h-80 w-full rounded-lg border border-neutral-200 dark:border-neutral-700"
      />
    );
  }

  return (
    <div className="flex h-40 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-neutral-300 text-xs text-neutral-400 dark:border-neutral-600">
      <FileText size={20} />
      <a href={attachment.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline dark:text-blue-400">
        새 탭에서 열기
      </a>
    </div>
  );
}
