import smtplib
from email.message import EmailMessage

from app.core.email_config import email_settings


class EmailService:
    """SMTP 설정이 있을 때 이메일 인증 코드를 발송합니다."""

    @property
    def is_configured(self) -> bool:
        return bool(email_settings.smtp_host and email_settings.smtp_from_email)

    def send_verification_code(self, recipient: str, code: str) -> bool:
        if not self.is_configured:
            return False

        message = EmailMessage()
        message["Subject"] = "TheGPT 이메일 인증 코드"
        message["From"] = email_settings.smtp_from_email
        message["To"] = recipient
        message.set_content(f"TheGPT 이메일 인증 코드는 {code}입니다. 10분 안에 입력해주세요.")

        with smtplib.SMTP(email_settings.smtp_host, email_settings.smtp_port) as smtp:
            if email_settings.smtp_use_tls:
                smtp.starttls()
            if email_settings.smtp_username and email_settings.smtp_password:
                smtp.login(email_settings.smtp_username, email_settings.smtp_password)
            smtp.send_message(message)
        return True


email_service = EmailService()
