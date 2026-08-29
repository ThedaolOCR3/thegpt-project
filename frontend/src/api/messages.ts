import { apiClient } from '../services/apiClient';
import { withChatToken } from '../features/auth/guestSession';
import type { Message, MessageAttachment } from './types';

interface MessageAttachmentDto {
  id: string;
  file_name: string;
  file_type: string | null;
  file_size_bytes: number | null;
}

interface MessageDto {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  attachments: MessageAttachmentDto[];
}

function toAttachment(dto: MessageAttachmentDto): MessageAttachment {
  return { name: dto.file_name, type: dto.file_type ?? undefined, size: dto.file_size_bytes ?? undefined };
}

function toMessage(dto: MessageDto): Message {
  return {
    id: dto.id,
    role: dto.role,
    content: dto.content,
    createdAt: dto.created_at,
    attachments: dto.attachments?.length ? dto.attachments.map(toAttachment) : undefined,
  };
}

export async function getMessages(conversationId: string): Promise<Message[]> {
  const list = await withChatToken((token) =>
    apiClient<MessageDto[]>(`/conversations/${conversationId}/messages`, { token }),
  );
  return list.map(toMessage);
}

/**
 * 사용자 메시지를 저장하고 assistant 응답을 받아온다.
 * 반환값은 assistant 응답 메시지 하나다 (사용자 메시지는 화면에서 낙관적으로 먼저 렌더링됨).
 *
 * 첨부파일은 이름/크기/타입 메타데이터만 서버에 저장된다 — 실제 파일 바이트는 아직
 * Object Storage(R2 등) 연동 전이라 전송하지 않는다. 원본 미리보기는 프론트에서
 * blob: URL로 그 세션 안에서만 보여준다 (ChatPage 참고).
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  files?: File[],
  modelId?: string,
): Promise<Message> {
  const dto = await withChatToken((token) =>
    apiClient<MessageDto>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      token,
      body: JSON.stringify({
        content,
        attachments: files?.map((f) => ({ name: f.name, size: f.size, type: f.type })) ?? [],
        // ModelSelect가 Backend의 Vast.ai Model Registry와 같은 ID를 사용한다.
        model_id: modelId,
      }),
    }),
  );
  return toMessage(dto);
}
