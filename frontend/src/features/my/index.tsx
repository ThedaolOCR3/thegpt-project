import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import './myPage.css';

export function MyPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <section className="my-page">
      <header><p>MY PAGE</p><h1>마이 페이지</h1></header>
      <div className="profile-panel">
        <div className="profile-image" aria-hidden="true">👤</div>
        <div><h2>프로필</h2><p>회원가입 시 입력한 계정 정보입니다.</p></div>
      </div>
      <div className="profile-form">
        <label>이메일<input value={user?.email ?? ''} readOnly /></label>
        <label>이메일 인증<input value={user?.is_email_verified ? '인증 완료' : '미인증'} readOnly /></label>
        <label>구독 등급<input value="free" readOnly /></label>
        <label>계정 권한<input value={user?.is_admin ? '관리자' : '일반 사용자'} readOnly /></label>
      </div>
      <button className="logout-button" onClick={handleLogout}>로그아웃</button>
    </section>
  );
}
