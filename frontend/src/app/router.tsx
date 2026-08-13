import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '../components/AppLayout';
import { MainLayout } from '../components/Layout/MainLayout';
import { LoginPage } from '../features/auth/login';
import { SignupPage } from '../features/auth/signup';
import { VerifyEmailPage } from '../features/auth/verify';
import { ForgotPasswordPage } from '../features/auth/password-reset/ForgotPasswordPage';
import { ResetPasswordPage } from '../features/auth/password-reset/ResetPasswordPage';
import { RequireAuth } from '../features/auth/RequireAuth';
import { AdminPage } from '../features/admin';
import { ConsultationPage } from '../features/consultation';
import { ChatPage } from '../features/chat';
import { DocumentPage } from '../features/document';
import { EvaluationPage } from '../features/evaluation';
import { OcrPage } from '../features/ocr';
import { SearchPage } from '../features/search';
import { MyPage } from '../features/my';

export const router = createBrowserRouter([
  {
    // 사이드바 기반 레이아웃 — 메인/채팅/마이페이지가 공유
    element: <MainLayout />,
    children: [
      { path: '/', element: <ConsultationPage /> },
      { path: '/chat/:conversationId', element: <ChatPage /> },
      {
        // 로그인한 사용자만 사이드바 마이페이지에 접근할 수 있습니다.
        element: <RequireAuth />,
        children: [{ path: '/mypage', element: <MyPage /> }],
      },
    ],
  },
  {
    // 기존 상단 nav 레이아웃 — 로그인/문서/OCR/검색/평가/관리자 (이번 작업 범위 아님, 그대로 둠)
    element: <AppLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      { path: '/verify-email', element: <VerifyEmailPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password', element: <ResetPasswordPage /> },
      { path: '/document', element: <DocumentPage /> },
      { path: '/ocr', element: <OcrPage /> },
      { path: '/search', element: <SearchPage /> },
      { path: '/evaluation', element: <EvaluationPage /> },
      { path: '/admin', element: <AdminPage /> },
      { path: '/my', element: <RequireAuth />, children: [{ index: true, element: <MyPage /> }] },
    ],
  },
]);
