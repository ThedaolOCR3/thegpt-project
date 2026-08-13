from io import BytesIO

import boto3

from app.core.storage_config import storage_settings


class R2StorageService:
    """Cloudflare R2의 S3 호환 API를 통해 파일을 저장합니다."""

    def _client(self):
        storage_settings.validate_r2()
        return boto3.client(
            service_name="s3",
            endpoint_url=f"https://{storage_settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=storage_settings.r2_access_key_id,
            aws_secret_access_key=storage_settings.r2_secret_access_key,
            region_name="auto",
        )

    def upload(self, content: bytes, key: str, content_type: str) -> str:
        self._client().upload_fileobj(
            BytesIO(content),
            storage_settings.r2_bucket_name,
            key,
            ExtraArgs={"ContentType": content_type, "CacheControl": "public, max-age=31536000"},
        )
        return f"{storage_settings.r2_public_url.rstrip('/')}/{key}"


r2_storage = R2StorageService()
