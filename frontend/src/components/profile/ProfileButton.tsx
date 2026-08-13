import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/AuthContext';
import './profileButton.css';

export function ProfileButton() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  return (
    <button
      aria-label={user ? '마이 페이지로 이동' : '로그인 페이지로 이동'}
      className="profile-button"
      disabled={isLoading}
      onClick={() => navigate(user ? '/my' : '/login')}
    >
      {user?.profile_image_url
        ? <img src={user.profile_image_url} alt="프로필" />
        : <span aria-hidden="true">👤</span>}
    </button>
  );
}
