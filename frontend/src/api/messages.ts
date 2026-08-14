import { apiClient } from '../services/apiClient';
import { getChatToken } from '../features/auth/guestSession';
import type { Message } from './types';

interface MessageDto {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

function toMessage(dto: MessageDto): Message {
  return { id: dto.id, role: dto.role, content: dto.content, createdAt: dto.created_at };
}

export async function getMessages(conversationId: string): Promise<Message[]> {
  const token = await getChatToken();
  const list = await apiClient<MessageDto[]>(`/conversations/${conversationId}/messages`, { token });
  return list.map(toMessage);
}

/**
 * 사용자 메시지를 저장하고 assistant 응답을 받아온다.
 * 반환값은 assistant 응답 메시지 하나다 (사용자 메시지는 화면에서 낙관적으로 먼저 렌더링됨).
 *
 * TODO: files는 아직 서버로 전송하지 않는다 — Object Storage(R2 등) 연동 전까지는
 * 첨부파일 없이 텍스트만 저장된다. 스토리지가 붙으면 FormData 기반 업로드로 교체.
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  files?: File[],
): Promise<Message> {
  const token = await getChatToken();
  const dto = await apiClient<MessageDto>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    token,
    body: JSON.stringify({ content }),
  });
  return toMessage(dto);
}
