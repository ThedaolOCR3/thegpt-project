import { apiClient } from '../services/apiClient';
import { getChatToken } from '../features/auth/guestSession';
import type { Conversation } from './types';

// 백엔드 응답은 DB 컬럼명 그대로 snake_case로 온다 (app/schemas/conversation.py 참고).
// 화면 쪽 코드가 쓰는 camelCase 타입(Conversation)으로는 여기서만 변환한다.
interface ConversationDto {
  id: string;
  title: string | null;
  is_title_custom: boolean;
  category: string | null;
  updated_at: string;
}

function toConversation(dto: ConversationDto): Conversation {
  return {
    id: dto.id,
    title: dto.title ?? '새 대화',
    isTitleCustom: dto.is_title_custom,
    category: dto.category ?? undefined,
    updatedAt: dto.updated_at,
  };
}

export async function getConversations(): Promise<Conversation[]> {
  const token = await getChatToken();
  const list = await apiClient<ConversationDto[]>('/conversations', { token });
  return list.map(toConversation);
}

export async function createConversation(): Promise<Conversation> {
  const token = await getChatToken();
  const dto = await apiClient<ConversationDto>('/conversations', { method: 'POST', token });
  return toConversation(dto);
}

export async function renameConversation(id: string, title: string): Promise<void> {
  const token = await getChatToken();
  await apiClient(`/conversations/${id}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(id: string): Promise<void> {
  const token = await getChatToken();
  await apiClient(`/conversations/${id}`, { method: 'DELETE', token });
}
