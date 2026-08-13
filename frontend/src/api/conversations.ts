import type { Conversation } from './types';
import { conversations, messagesByConversation, delay, generateId } from './mockStore';

// TODO: 백엔드 연동 시 아래 mock 구현을 실제 fetch('/api/v1/conversations', ...) 호출로 교체.
// 함수 시그니처(입출력 타입)는 그대로 유지하면 화면 쪽 코드는 수정할 필요 없음.

export async function getConversations(): Promise<Conversation[]> {
  await delay();
  return [...conversations].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );
}

export async function createConversation(): Promise<Conversation> {
  await delay();
  const conversation: Conversation = {
    id: generateId('conv'),
    title: '새 대화',
    isTitleCustom: false,
    updatedAt: new Date().toISOString(),
  };
  conversations.unshift(conversation);
  messagesByConversation[conversation.id] = [];
  return conversation;
}

export async function renameConversation(id: string, title: string): Promise<void> {
  await delay(150);
  const conversation = conversations.find((c) => c.id === id);
  if (!conversation) return;
  conversation.title = title;
  conversation.isTitleCustom = true;
  conversation.updatedAt = new Date().toISOString();
}

export async function deleteConversation(id: string): Promise<void> {
  await delay(150);
  const index = conversations.findIndex((c) => c.id === id);
  if (index !== -1) conversations.splice(index, 1);
  delete messagesByConversation[id];
}
