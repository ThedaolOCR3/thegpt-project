# 이메일 인증 설정

## 동작 흐름

1. 프론트엔드가 `POST /api/auth/signup`으로 이메일과 비밀번호를 보냅니다.
2. 백엔드는 비밀번호를 Argon2로 해시해 `app_db.users`에 저장합니다.
3. 6자리 인증 코드를 생성해 `app_db.email_verifications`에 10분 만료로 저장합니다.
4. SMTP가 설정돼 있으면 사용자 이메일로 코드를 전송합니다.
5. 사용자가 코드를 입력하면 `POST /api/auth/verify-email`에서 코드와 만료 시간을 확인합니다.
6. 인증에 성공하면 `users.is_email_verified`가 `true`로 변경됩니다.
7. 인증된 사용자만 로그인할 수 있습니다.

## SMTP 환경변수

프로젝트 최상위 `.env`에 사용하는 메일 서비스의 SMTP 정보를 입력합니다.

```env
APP_ENV=production
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=no-reply@example.com
SMTP_USE_TLS=true
```

메일 서비스에서 제공하는 SMTP 호스트, 포트, 사용자명과 비밀번호를 사용해야 합니다.
개인 이메일 계정을 사용할 경우 일반 로그인 비밀번호 대신 앱 비밀번호가 필요할 수 있습니다.

## 로컬 개발

SMTP 값을 비워두고 `APP_ENV=local`로 실행하면 메일을 보내지 않고 회원가입 API 응답에
`dev_verification_code`가 포함됩니다. 프론트엔드는 이 값을 인증 화면에 표시합니다.

운영 환경에서는 반드시 다음을 지켜야 합니다.

- `APP_ENV=production`으로 설정합니다.
- 충분히 긴 임의 문자열을 `JWT_SECRET_KEY`에 사용합니다.
- `.env`를 Git에 커밋하지 않습니다.
- SMTP 인증 정보는 배포 환경의 Secret으로 관리합니다.
