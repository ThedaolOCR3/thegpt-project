import { NavLink, Outlet } from 'react-router-dom';
import { ProfileButton } from './profile/ProfileButton';

const links = [
  ['/', '상담'],
  ['/document', '문서 업로드'],
  ['/ocr', 'OCR'],
  ['/search', '검색'],
  ['/evaluation', '평가'],
  ['/admin', '관리자'],
];

export function AppLayout() {
  return (
    <>
      <header className="app-header">
        <NavLink className="app-logo" to="/">TheGPT</NavLink>
        <nav>
          {links.map(([path, label]) => <NavLink key={path} to={path}>{label}</NavLink>)}
        </nav>
        <ProfileButton />
      </header>
      <main><Outlet /></main>
    </>
  );
}
