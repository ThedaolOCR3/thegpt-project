import { useState } from 'react';
import { Check, Copy, FileText } from 'lucide-react';
import type { Message, MessageAttachment } from '../../api/types';
import { formatMessageTime } from '../../utils/formatDate';

type MessageBubbleProps = {
  message: Message;
  onPreviewAttachment?: (attachments: MessageAttachment[], index: number) => void;
};

export function MessageBubble({ message, onPreviewAttachment }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      // 2초 뒤 아이콘을 원래대로 되돌린다 — 매번 새 타이머라 겹쳐 눌러도 마지막 클릭 기준으로 리셋됨.
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // 클립보드 권한이 없는 브라우저/환경 — 조용히 무시(복사 버튼 자체가 부가 기능이라 에러 UI까지는 안 둠).
    }
  }

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      <div className="max-w-[70%]">
        {message.content && (
          <div
            className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
              isUser
                ? 'bg-blue-100 text-neutral-900 dark:bg-blue-900 dark:text-blue-50'
                : 'border border-neutral-200 bg-white text-neutral-800 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100'
            }`}
          >
            {message.content}
          </div>
        )}

        {message.attachments && message.attachments.length > 0 && (
          <div className={`mt-1.5 flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
            {message.attachments.map((file, index) => (
              <button
                key={file.name}
                type="button"
                onClick={() => onPreviewAttachment?.(message.attachments!, index)}
                title="원본/파싱 결과 미리보기"
                className="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1.5 text-xs text-neutral-600 hover:bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700"
              >
                <FileText size={12} />
                {file.name}
                <span className="text-blue-600 dark:text-blue-400">미리보기</span>
              </button>
            ))}
          </div>
        )}

        <div
          className={`mt-1 flex items-center gap-2 text-[11px] text-neutral-400 dark:text-neutral-500 ${
            isUser ? 'justify-end' : 'justify-start'
          }`}
        >
          {!isUser && message.content && (
            <button
              type="button"
              onClick={handleCopy}
              title="답변 복사"
              aria-label="답변 복사"
              className="flex items-center gap-1 rounded p-0.5 hover:text-neutral-600 dark:hover:text-neutral-300"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied && <span>복사됨</span>}
            </button>
          )}
          <span>{formatMessageTime(message.createdAt)}</span>
        </div>
      </div>
    </div>
  );
}
