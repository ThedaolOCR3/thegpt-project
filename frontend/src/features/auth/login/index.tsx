import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { AuthCard } from '../components/AuthCard';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      // 로그인에 성공하면 항상 메인 페이지로 이동합니다.
      navigate('/', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '로그인에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthCard title="로그인" description="계정으로 로그인하고 상담 기록을 확인하세요.">
      <form className="auth-form" onSubmit={submit}>
        <div className="auth-field"><label htmlFor="login-email">이메일</label><input id="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
        <div className="auth-field"><label htmlFor="login-password">비밀번호</label><input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
        <div className="password-help"><Link to="/forgot-password">비밀번호를 잊으셨나요?</Link></div>
        {error && <p className="form-error">{error}</p>}
        <button className="auth-button" disabled={isSubmitting}>{isSubmitting ? '로그인 중...' : '로그인'}</button>
      </form>
      <p className="auth-links">계정이 없나요? <Link to="/signup">회원가입</Link></p>
    </AuthCard>
  );
}
