import { FileText } from 'lucide-react';
import type { Message, MessageAttachment } from '../../api/types';

type MessageBubbleProps = {
  message: Message;
  onPreviewAttachment?: (attachments: MessageAttachment[], index: number) => void;
};

export function MessageBubble({ message, onPreviewAttachment }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
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
      </div>
    </div>
  );
}
