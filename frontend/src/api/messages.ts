import type { Message } from './types';
import { conversations, messagesByConversation, delay, generateId, createMockAssistantReply } from './mockStore';

// TODO: 백엔드 연동 시 아래 mock 구현을 실제 fetch('/api/v1/conversations/:id/messages', ...) 호출로 교체.

export async function getMessages(conversationId: string): Promise<Message[]> {
  await delay();
  return messagesByConversation[conversationId] ?? [];
}

/**
 * 사용자 메시지를 저장하고, mock 지연 후 assistant 응답을 생성해 저장한다.
 * 반환값은 assistant 응답 메시지 하나다 (사용자 메시지는 화면에서 낙관적으로 먼저 렌더링하면 됨).
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  files?: File[],
): Promise<Message> {
  if (!messagesByConversation[conversationId]) {
    messagesByConversation[conversationId] = [];
  }

  const userMessage: Message = {
    id: generateId('msg'),
    role: 'user',
    content,
    createdAt: new Date().toISOString(),
    attachments: files?.length ? files.map((f) => ({ name: f.name })) : undefined,
  };
  messagesByConversation[conversationId].push(userMessage);

  const conversation = conversations.find((c) => c.id === conversationId);
  if (conversation) conversation.updatedAt = userMessage.createdAt;

  await delay(600);

  const assistantMessage: Message = {
    id: generateId('msg'),
    role: 'assistant',
    content: createMockAssistantReply(content),
    createdAt: new Date().toISOString(),
  };
  messagesByConversation[conversationId].push(assistantMessage);

  return assistantMessage;
}
