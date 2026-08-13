import { useEffect, useRef, useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import type { Conversation } from '../../api/types';

type HistoryItemProps = {
  conversation: Conversation;
  active: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
};

export function HistoryItem({ conversation, active, onSelect, onRename, onDelete }: HistoryItemProps) {
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(conversation.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function startEditing() {
    setDraftTitle(conversation.title);
    setEditing(true);
  }

  function commit() {
    const trimmed = draftTitle.trim();
    setEditing(false);
    if (trimmed && trimmed !== conversation.title) onRename(trimmed);
  }

  function cancel() {
    setDraftTitle(conversation.title);
    setEditing(false);
  }

  function handleDelete() {
    if (window.confirm(`'${conversation.title}' 대화를 삭제할까요?`)) onDelete();
  }

  return (
    <div
      className={`group relative flex flex-col rounded-lg px-3 py-2 cursor-pointer ${
        active ? 'bg-blue-50 dark:bg-blue-950' : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'
      }`}
      onClick={editing ? undefined : onSelect}
    >
      {editing ? (
        <input
          ref={inputRef}
          value={draftTitle}
          onChange={(e) => setDraftTitle(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') cancel();
          }}
          className="w-full rounded border border-blue-300 bg-white px-1.5 py-0.5 text-sm outline-none dark:border-blue-700 dark:bg-neutral-900 dark:text-neutral-100"
          autoFocus
        />
      ) : (
        <div className="flex items-center justify-between gap-1">
          <span className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-100">
            {conversation.title}
          </span>
          <div className="hidden shrink-0 items-center gap-1 group-hover:flex">
            <button
              type="button"
              title="제목 수정"
              aria-label="제목 수정"
              onClick={(e) => {
                e.stopPropagation();
                startEditing();
              }}
              className="rounded p-1 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700 dark:hover:bg-neutral-700 dark:hover:text-neutral-200"
            >
              <Pencil size={13} />
            </button>
            <button
              type="button"
              title="대화 삭제"
              aria-label="대화 삭제"
              onClick={(e) => {
                e.stopPropagation();
                handleDelete();
              }}
              className="rounded p-1 text-neutral-400 hover:bg-neutral-200 hover:text-red-500 dark:hover:bg-neutral-700 dark:hover:text-red-400"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      )}
      {conversation.category && !editing && (
        <span className="text-xs text-neutral-400 dark:text-neutral-500">{conversation.category}</span>
      )}
    </div>
  );
}
