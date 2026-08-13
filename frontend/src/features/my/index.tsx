import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PasswordChangeModal } from './password-change/PasswordChangeModal';
import './myPage.css';

export function MyPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <section className="my-page overflow-y-auto p-8">
      <header><p>MY PAGE</p><h1>마이 페이지</h1></header>
      <div className="profile-panel">
        <div className="profile-image" aria-hidden="true">👤</div>
        <div><h2>프로필</h2><p>회원가입 시 입력한 계정 정보입니다.</p></div>
      </div>
      <div className="profile-form">
        <label>
          <span className="email-label">
            이메일
            <span className={user?.is_email_verified ? 'verification-status verified' : 'verification-status unverified'}>
              <span className="status-dot" aria-hidden="true" />
              {user?.is_email_verified ? '( 인증된 유저 )' : '( 인증이 안된 유저 )'}
            </span>
          </span>
          <input value={user?.email ?? ''} readOnly />
        </label>
      </div>
      <div className="profile-actions">
        <button className="password-change-button" onClick={() => setIsPasswordModalOpen(true)}>비밀번호 변경</button>
        <button className="logout-button" onClick={handleLogout}>로그아웃</button>
      </div>
      {isPasswordModalOpen && <PasswordChangeModal onClose={() => setIsPasswordModalOpen(false)} />}
    </section>
  );
}
