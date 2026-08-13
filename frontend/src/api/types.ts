export interface Conversation {
  id: string;
  title: string;
  isTitleCustom: boolean;
  category?: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  /** 스펙 기본 타입에는 없지만, 문서 미리보기 패널을 위해 추가한 선택 필드. */
  attachments?: { name: string }[];
}
