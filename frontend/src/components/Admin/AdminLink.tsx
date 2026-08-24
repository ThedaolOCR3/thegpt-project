import { LayoutDashboard } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../features/auth/AuthContext';

/** 라이트/다크모드 토글 옆에 두는 관리자 대시보드 이동 버튼.
 * 관리자(is_admin) 계정이 아니면 버튼 자체를 렌더링하지 않는다. */
export function AdminLink() {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.is_admin);

  if (!isAdmin) {
    return null;
  }

  return (
    <Link
      to="/admin"
      title="관리자 대시보드로 이동"
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors hover:bg-neutral-200 hover:text-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-700 dark:hover:text-white"
    >
      <LayoutDashboard size={16} />
    </Link>
  );
}
