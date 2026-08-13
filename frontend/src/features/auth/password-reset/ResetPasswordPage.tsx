import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AuthCard } from '../components/AuthCard';
import { passwordResetApi } from './passwordResetApi';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState(''); const [confirm, setConfirm] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState(token ? '' : '재설정 토큰이 없습니다. 이메일 링크를 다시 확인해주세요.');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (password !== confirm) { setError('비밀번호 확인이 일치하지 않습니다.'); return; }
    setError(''); setIsSubmitting(true);
    try {
      const result = await passwordResetApi.reset(token, password);
      setNotice(result.message); setPassword(''); setConfirm('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '비밀번호 변경에 실패했습니다.');
    } finally { setIsSubmitting(false); }
  };

  return <AuthCard title="비밀번호 재설정" description="새로 사용할 비밀번호를 입력해주세요.">
    <form className="auth-form" onSubmit={submit}>
      <div className="auth-field"><label htmlFor="new-password">새 비밀번호</label><input id="new-password" type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
      <div className="auth-field"><label htmlFor="confirm-password">비밀번호 확인</label><input id="confirm-password" type="password" minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)} required /></div>
      {notice && <p className="form-notice">{notice}</p>}{error && <p className="form-error">{error}</p>}
      <button className="auth-button" disabled={isSubmitting || !token}>{isSubmitting ? '변경 중...' : '비밀번호 변경'}</button>
    </form>
    <p className="auth-links"><Link to="/login">로그인으로 이동</Link></p>
  </AuthCard>;
}
