import { NavLink, Outlet } from 'react-router-dom';

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
      <nav>
        {links.map(([path, label]) => <NavLink key={path} to={path}>{label}</NavLink>)}
      </nav>
      <main><Outlet /></main>
    </>
  );
}

