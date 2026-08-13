import type { Conversation, Message } from './types';

// 실제 백엔드가 붙기 전까지 conversations.ts / messages.ts가 공유하는 인메모리 저장소.
// FastAPI 연동 시 이 파일 전체를 실제 fetch 호출로 교체하면 된다 (함수 시그니처는 그대로 유지).

export function delay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function generateId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export const conversations: Conversation[] = [
  {
    id: 'conv_diabetes',
    title: '당뇨 초기 증상 문의',
    isTitleCustom: false,
    category: '내분비내과',
    updatedAt: '2026-08-11T09:00:00.000Z',
  },
  {
    id: 'conv_mri',
    title: 'MRI 판독 관련 질문',
    isTitleCustom: false,
    category: '영상의학과',
    updatedAt: '2026-08-10T09:00:00.000Z',
  },
  {
    id: 'conv_cold',
    title: '감기 지속 시 대처법',
    isTitleCustom: false,
    category: '가정의학과',
    updatedAt: '2026-08-09T09:00:00.000Z',
  },
];

export const messagesByConversation: Record<string, Message[]> = {
  conv_diabetes: [
    {
      id: generateId('msg'),
      role: 'user',
      content: '초기 당뇨 증상이 궁금해요 🙋',
      createdAt: '2026-08-11T09:00:00.000Z',
    },
    {
      id: generateId('msg'),
      role: 'assistant',
      content: '초기 당뇨는 갈증, 잦은 소변, 피로감 등이 대표적인 증상이에요...',
      createdAt: '2026-08-11T09:00:05.000Z',
    },
  ],
  conv_mri: [
    {
      id: generateId('msg'),
      role: 'user',
      content: '이 MRI 사진 판독 결과가 궁금해요',
      createdAt: '2026-08-10T09:00:00.000Z',
      attachments: [{ name: 'brain_mri_slice12.png' }],
    },
    {
      id: generateId('msg'),
      role: 'assistant',
      content:
        '첨부해주신 파일을 확인했어요. 우측에서 원본과 파싱된 텍스트를 비교해보실 수 있어요. (Mock 응답 — 실제 판독 연동 전)',
      createdAt: '2026-08-10T09:00:05.000Z',
    },
  ],
  conv_cold: [],
};

const MOCK_ASSISTANT_REPLIES = [
  '입력하신 내용을 확인했어요. 관련 정보를 정리해서 안내드릴게요. (Mock 응답 — 실제 LLM 연동 전)',
  '말씀하신 증상을 참고해서 답변드릴게요. (Mock 응답 — 실제 LLM 연동 전)',
  '조금 더 자세히 살펴본 뒤 안내드릴게요. (Mock 응답 — 실제 LLM 연동 전)',
];

export function createMockAssistantReply(userContent: string): string {
  const template = MOCK_ASSISTANT_REPLIES[Math.floor(Math.random() * MOCK_ASSISTANT_REPLIES.length)];
  return `"${userContent}"에 대해 ${template}`;
}
