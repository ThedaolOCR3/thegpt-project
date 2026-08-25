"""OCR Chunk를 Gemini의 1024차원 Vector로 변환합니다."""

import asyncio
import logging
import math
from collections.abc import Callable
from typing import Any, Protocol

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Embedding 단계에서 처리 가능한 오류의 공통 부모입니다."""


class EmbeddingUnavailableError(EmbeddingServiceError):
    """API Key 또는 Embedding Provider를 사용할 수 없을 때 발생합니다."""


class EmbeddingGenerationError(EmbeddingServiceError):
    """Provider 호출이 실패하거나 유효하지 않은 응답을 반환할 때 발생합니다."""


class EmbeddingValidationError(EmbeddingServiceError):
    """Chunk 또는 Vector가 DB 저장 계약을 만족하지 않을 때 발생합니다."""


class EmbeddingService(Protocol):
    """중심 OCR Service가 Provider 종류와 무관하게 사용하는 공통 계약입니다."""

    provider: str
    model: str
    dimension: int

    async def embed_chunks(self, chunks: list[str]) -> list[list[float]]: ...


def _create_google_client(api_key: str) -> Any:
    from google import genai

    return genai.Client(api_key=api_key)


class GeminiEmbeddingService:
    """Google GenAI 배치 API로 Chunk 순서와 개수를 유지해 임베딩합니다."""

    provider = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        dimension: int,
        timeout_seconds: float,
        client_factory: Callable[[str], Any] = _create_google_client,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.model = model.strip()
        self.dimension = dimension
        self.timeout_seconds = max(1.0, timeout_seconds)
        self._client_factory = client_factory

    async def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """빈 Chunk를 거부하고 각 입력과 같은 순서의 1024차원 Vector를 반환합니다."""

        self._validate_chunks(chunks)
        if not self.api_key:
            raise EmbeddingUnavailableError(
                "최상위 .env에 GEMINI_API_KEY를 설정해야 OCR Chunk를 저장할 수 있습니다."
            )

        logger.info(
            "[EMBEDDING] embedding start: model=%s chunks=%d dimension=%d",
            self.model,
            len(chunks),
            self.dimension,
        )
        client: Any = None
        async_client: Any = None
        try:
            client = self._client_factory(self.api_key)
            async_client = client.aio
            response = await asyncio.wait_for(
                async_client.models.embed_content(
                    model=self.model,
                    contents=chunks,
                    config={
                        "task_type": "RETRIEVAL_DOCUMENT",
                        "output_dimensionality": self.dimension,
                    },
                ),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            logger.warning("[EMBEDDING] provider timeout: model=%s", self.model)
            raise EmbeddingGenerationError("Embedding 생성 제한시간을 초과했습니다.") from exc
        except EmbeddingServiceError:
            raise
        except Exception as exc:
            # API Key나 Chunk 원문이 로그 또는 응답에 노출되지 않도록 오류 형식만 기록합니다.
            logger.warning(
                "[EMBEDDING] provider failed: model=%s error_type=%s",
                self.model,
                type(exc).__name__,
            )
            raise EmbeddingGenerationError("Embedding 생성에 실패했습니다.") from exc
        finally:
            await self._close_clients(async_client, client)

        embeddings = self._extract_embeddings(response, expected_count=len(chunks))
        logger.info("[EMBEDDING] embedding complete: vectors=%d", len(embeddings))
        return embeddings

    def _validate_chunks(self, chunks: list[str]) -> None:
        if not chunks:
            raise EmbeddingValidationError("저장할 OCR Chunk가 없습니다.")
        if any(not isinstance(chunk, str) or not chunk.strip() for chunk in chunks):
            raise EmbeddingValidationError("빈 OCR Chunk는 Embedding으로 저장할 수 없습니다.")
        if self.dimension != 1024:
            raise EmbeddingValidationError(
                "EMBEDDING_DIMENSION은 document_chunks.embedding의 1024차원과 같아야 합니다."
            )

    def _extract_embeddings(self, response: Any, *, expected_count: int) -> list[list[float]]:
        response_embeddings = getattr(response, "embeddings", None) or []
        if len(response_embeddings) != expected_count:
            raise EmbeddingValidationError(
                f"OCR Chunk는 {expected_count}개지만 Embedding은 {len(response_embeddings)}개입니다."
            )

        vectors: list[list[float]] = []
        for embedding in response_embeddings:
            values = getattr(embedding, "values", None)
            if values is None:
                raise EmbeddingGenerationError("Embedding Provider가 빈 Vector를 반환했습니다.")
            try:
                vector = [float(value) for value in values]
            except (TypeError, ValueError) as exc:
                raise EmbeddingValidationError(
                    "Embedding Vector에 숫자가 아닌 값이 있습니다."
                ) from exc
            if len(vector) != self.dimension:
                raise EmbeddingValidationError(
                    f"Embedding Vector 차원은 {self.dimension}이어야 하지만 {len(vector)}입니다."
                )
            if any(not math.isfinite(value) for value in vector):
                raise EmbeddingValidationError("Embedding Vector에 유효하지 않은 숫자가 있습니다.")
            vectors.append(vector)
        return vectors

    @staticmethod
    async def _close_clients(async_client: Any, client: Any) -> None:
        if async_client is not None and callable(getattr(async_client, "aclose", None)):
            try:
                await async_client.aclose()
            except Exception:
                pass
        if client is not None and callable(getattr(client, "close", None)):
            try:
                client.close()
            except Exception:
                pass


EmbeddingProviderFactory = Callable[[Settings], EmbeddingService]


def _create_gemini_embedding_service(app_settings: Settings) -> EmbeddingService:
    return GeminiEmbeddingService(
        api_key=app_settings.gemini_api_key,
        model=app_settings.embedding_model,
        dimension=app_settings.embedding_dimension,
        timeout_seconds=app_settings.embedding_timeout_seconds,
    )


# 향후 BGE-M3가 확정되면 공통 계약을 구현한 Provider factory만 이 Registry에 추가합니다.
EMBEDDING_PROVIDER_FACTORIES: dict[str, EmbeddingProviderFactory] = {
    "gemini": _create_gemini_embedding_service,
}


def create_embedding_service(app_settings: Settings = settings) -> EmbeddingService:
    """설정된 Provider 이름으로 Embedding 구현체를 선택합니다."""

    provider = app_settings.embedding_provider.strip().lower()
    factory = EMBEDDING_PROVIDER_FACTORIES.get(provider)
    if factory is None:
        supported = ", ".join(sorted(EMBEDDING_PROVIDER_FACTORIES))
        raise EmbeddingUnavailableError(
            f"지원하지 않는 Embedding Provider입니다: {provider}. 지원 목록: {supported}"
        )
    return factory(app_settings)


embedding_service = create_embedding_service()
