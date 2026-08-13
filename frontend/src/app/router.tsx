import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '../components/AppLayout';
import { MainLayout } from '../components/Layout/MainLayout';
import { LoginPage } from '../features/auth/login';
import { SignupPage } from '../features/auth/signup';
import { AdminPage } from '../features/admin';
import { ConsultationPage } from '../features/consultation';
import { ChatPage } from '../features/chat';
import { MyPage } from '../features/mypage';
import { DocumentPage } from '../features/document';
import { EvaluationPage } from '../features/evaluation';
import { OcrPage } from '../features/ocr';
import { SearchPage } from '../features/search';

export const router = createBrowserRouter([
  {
    // 사이드바 기반 레이아웃 — 메인/채팅/마이페이지가 공유
    element: <MainLayout />,
    children: [
      { path: '/', element: <ConsultationPage /> },
      { path: '/chat/:conversationId', element: <ChatPage /> },
      { path: '/mypage', element: <MyPage /> },
    ],
  },
  {
    // 기존 상단 nav 레이아웃 — 로그인/문서/OCR/검색/평가/관리자 (이번 작업 범위 아님, 그대로 둠)
    element: <AppLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      { path: '/document', element: <DocumentPage /> },
      { path: '/ocr', element: <OcrPage /> },
      { path: '/search', element: <SearchPage /> },
      { path: '/evaluation', element: <EvaluationPage /> },
      { path: '/admin', element: <AdminPage /> },
    ],
  },
]);

