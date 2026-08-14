import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { MessageInput } from '../../components/Chat/MessageInput';
import { MessageBubble } from '../../components/Chat/MessageBubble';
import { useDocumentPreview } from '../../components/Chat/DocumentPreviewContext';
import { getMessages, sendMessage } from '../../api/messages';
import { generateId } from '../../utils/id';
import type { Message } from '../../api/types';

type LocationState = {
  pendingMessage?: string;
  pendingFiles?: File[];
} | null;

export function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const { openPreview } = useDocumentPreview();
  const bottomRef = useRef<HTMLDivElement>(null);
  // StrictMode(개발 모드)는 effect를 두 번 실행하므로, pendingMessage를 이미
  // 처리했는지 conversationId별로 기록해 중복 전송을 막는다.
  const handledPendingFor = useRef<string | null>(null);
  // pendingMessage 흐름이 이 conversationId의 메시지를 불러와 전송하는 동안에만 켜진다.
  // (실제 백엔드는 mock과 달리 요청마다 왕복 시간이 있어서, StrictMode의 두 번째 effect
  // 실행이 else 분기의 getMessages를 그 사이에 끼워 넣으면 낙관적으로 추가한 사용자
  // 메시지가 덮어써져 사라지는 레이스 컨디션이 생긴다 — 그래서 진행 중엔 else 분기를 건너뛴다.
  // handledPendingFor와 달리 흐름이 끝나면 다시 null로 돌아가므로, 나중에 같은 대화를
  // 재방문했을 때의 정상적인 메시지 로드는 막지 않는다.)
  const pendingSendInFlightFor = useRef<string | null>(null);

  // 대화 전환 시 메시지 로드. 메인 화면에서 막 넘어온 경우(pendingMessage)라면
  // 그 메시지를 곧바로 전송하는 흐름을 이어간다.
  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;

    async function load() {
      const state = location.state as LocationState;
      const hasPending = Boolean(state?.pendingMessage) && handledPendingFor.current !== conversationId;

      if (hasPending) {
        handledPendingFor.current = conversationId!;
        pendingSendInFlightFor.current = conversationId!;
        // react-router의 history를 통해 state를 비워야 실제로 초기화된다
        // (window.history.replaceState를 직접 쓰면 useLocation에 반영되지 않아
        // StrictMode 재실행 시 같은 state를 다시 읽어 중복 전송된다).
        navigate(location.pathname, { replace: true, state: null });
        // 위에서 이미 "이 conversationId의 pendingMessage는 처리한다"고 확정했으므로,
        // 여기서부터는 cancelled를 확인하지 않고 끝까지 진행한다.
        try {
          const existing = await getMessages(conversationId!);
          setMessages(existing);
          await sendUserMessage(state!.pendingMessage!, state!.pendingFiles ?? []);
        } finally {
          pendingSendInFlightFor.current = null;
        }
      } else if (pendingSendInFlightFor.current !== conversationId) {
        const existing = await getMessages(conversationId!);
        if (!cancelled) setMessages(existing);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function sendUserMessage(content: string, files: File[]) {
    if (!conversationId) return;

    const optimisticUserMessage: Message = {
      id: generateId('msg'),
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
      attachments: files.length ? files.map((f) => ({ name: f.name })) : undefined,
    };
    setMessages((current) => [...current, optimisticUserMessage]);

    setSending(true);
    try {
      const assistantMessage = await sendMessage(conversationId, content, files);
      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      // 게스트 메시지 한도 초과(429) 등 서버가 준 에러 메시지를 그대로 보여준다.
      const errorMessage: Message = {
        id: generateId('msg'),
        role: 'assistant',
        content: error instanceof Error ? error.message : '메시지를 보내지 못했어요. 잠시 후 다시 시도해주세요.',
        createdAt: new Date().toISOString(),
      };
      setMessages((current) => [...current, errorMessage]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 px-6 py-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} onPreviewAttachment={openPreview} />
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm text-neutral-400 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-500">
                  답변을 작성하고 있어요...
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="mx-auto w-full max-w-3xl px-6 pb-6">
          <MessageInput onSend={sendUserMessage} disabled={sending} placeholder="메시지를 입력하세요" />
        </div>
      </div>
    </div>
  );
}
