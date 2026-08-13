import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '../components/AppLayout';
import { LoginPage } from '../features/auth/login';
import { SignupPage } from '../features/auth/signup';
import { AdminPage } from '../features/admin';
import { ConsultationPage } from '../features/consultation';
import { DocumentPage } from '../features/document';
import { EvaluationPage } from '../features/evaluation';
import { OcrPage } from '../features/ocr';
import { SearchPage } from '../features/search';

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <ConsultationPage /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      { path: '/document', element: <DocumentPage /> },
      { path: '/consultation', element: <ConsultationPage /> },
      { path: '/ocr', element: <OcrPage /> },
      { path: '/search', element: <SearchPage /> },
      { path: '/evaluation', element: <EvaluationPage /> },
      { path: '/admin', element: <AdminPage /> },
    ],
  },
]);

