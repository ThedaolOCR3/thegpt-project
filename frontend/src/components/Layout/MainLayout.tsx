import { Outlet } from 'react-router-dom';
import { Sidebar, SidebarProvider } from '../Sidebar';
import { ThemeToggle } from '../Theme/ThemeToggle';
import { DocumentPreviewProvider, useDocumentPreview } from '../Chat/DocumentPreviewContext';
import { DocumentPreviewPanel } from '../Chat/DocumentPreviewPanel';

// 메인 화면(/)과 채팅 화면(/chat/:id), 마이페이지(/mypage)가 공유하는 레이아웃.
// 기존 상단 nav 기반 AppLayout(로그인/문서/OCR/검색/평가/관리자용)은 그대로 두고 건드리지 않음.
//
// Sidebar / 본문(main) / 문서 미리보기 패널을 같은 레벨의 형제로 둔다.
// 패널을 main 안쪽에 중첩시키면 우측 상단 다크모드 토글처럼 top-right에
// 고정되는 다른 UI와 자리가 겹치기 때문에, 구조적으로 분리했다.
export function MainLayout() {
  return (
    <SidebarProvider>
      <DocumentPreviewProvider>
        <MainLayoutBody />
      </DocumentPreviewProvider>
    </SidebarProvider>
  );
}

function MainLayoutBody() {
  const { preview, setPreviewIndex, closePreview } = useDocumentPreview();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white dark:bg-neutral-950">
      <Sidebar />
      <main className="relative flex min-w-0 flex-1 flex-col">
        <div className="absolute right-4 top-4 z-10">
          <ThemeToggle />
        </div>
        <Outlet />
      </main>
      {preview && (
        <DocumentPreviewPanel
          attachments={preview.attachments}
          index={preview.index}
          onIndexChange={setPreviewIndex}
          onClose={closePreview}
        />
      )}
    </div>
  );
}
