"""Bearer 인증을 사용하는 원격 Dense Embedding Provider입니다.

Vast.ai GPU 서버가 Jina v4와 Medical BGE-M3를 상주시키고, Backend은
이 Provider를 통해 query/passage Vector만 HTTP로 받습니다.
"""

import math
from collections.abc import Callable
from typing import Any, Literal

import httpx


class RemoteEmbeddingError(RuntimeError):
    """원격 Embedding 설정·호출·응답 검증이 실패했을 때 발생합니다."""


SyncClientFactory = Callable[..., httpx.Client]


class RemoteEmbeddingProvider:
    """`EmbeddingProvider` 계약을 만족하는 동기 HTTP Client입니다."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model: str,
        dimension: int = 1024,
        timeout_seconds: float = 60.0,
        batch_size: int = 32,
        name: str | None = None,
        transport: httpx.BaseTransport | None = None,
        client_factory: SyncClientFactory = httpx.Client,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip() if api_key else None
        self.model = model.strip()
        self.name = (name or self.model).strip()
        self.dimension = dimension
        self.timeout_seconds = max(1.0, timeout_seconds)
        self.batch_size = max(1, min(batch_size, 64))
        self._transport = transport
        self._client_factory = client_factory

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, input_type="passage")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], input_type="query")[0]

    def _embed(
        self,
        texts: list[str],
        *,
        input_type: Literal["query", "passage"],
    ) -> list[list[float]]:
        self._validate_configuration()
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise RemoteEmbeddingError("빈 Text는 Embedding할 수 없습니다.")

        client_kwargs: dict[str, Any] = {
            "timeout": httpx.Timeout(self.timeout_seconds),
        }
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        vectors: list[list[float]] = []
        try:
            with self._client_factory(**client_kwargs) as client:
                for start in range(0, len(texts), self.batch_size):
                    batch = texts[start : start + self.batch_size]
                    response = client.post(
                        f"{self.base_url}/v1/embeddings",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "input_type": input_type,
                            "texts": batch,
                        },
                    )
                    response.raise_for_status()
                    vectors.extend(
                        self._extract_vectors(
                            response.json(),
                            expected_count=len(batch),
                        )
                    )
        except httpx.TimeoutException as exc:
            raise RemoteEmbeddingError("Embedding 생성 제한시간을 초과했습니다.") from exc
        except httpx.HTTPStatusError as exc:
            raise RemoteEmbeddingError("원격 Embedding 서버가 요청을 거부했습니다.") from exc
        except httpx.RequestError as exc:
            raise RemoteEmbeddingError("원격 Embedding 서버에 연결하지 못했습니다.") from exc
        except RemoteEmbeddingError:
            raise
        except Exception as exc:
            raise RemoteEmbeddingError("원격 Embedding 응답을 처리하지 못했습니다.") from exc

        if len(vectors) != len(texts):
            raise RemoteEmbeddingError("요청 Text와 Embedding Vector 개수가 다릅니다.")
        return vectors

    def _extract_vectors(
        self,
        payload: Any,
        *,
        expected_count: int,
    ) -> list[list[float]]:
        if not isinstance(payload, dict):
            raise RemoteEmbeddingError("Embedding 서버가 JSON 객체를 반환하지 않았습니다.")
        if payload.get("model") != self.model:
            raise RemoteEmbeddingError("요청한 모델과 응답 모델이 일치하지 않습니다.")
        if payload.get("dimensions") != self.dimension:
            raise RemoteEmbeddingError(
                f"{self.model} Vector는 {self.dimension}차원이어야 합니다."
            )

        response_vectors = payload.get("embeddings")
        if not isinstance(response_vectors, list) or len(response_vectors) != expected_count:
            raise RemoteEmbeddingError("요청한 Text와 응답 Vector 개수가 다릅니다.")

        vectors: list[list[float]] = []
        for index, values in enumerate(response_vectors):
            if not isinstance(values, list):
                raise RemoteEmbeddingError(f"Vector {index}가 배열이 아닙니다.")
            try:
                vector = [float(value) for value in values]
            except (TypeError, ValueError) as exc:
                raise RemoteEmbeddingError(f"Vector {index}에 숫자가 아닌 값이 있습니다.") from exc
            if len(vector) != self.dimension:
                raise RemoteEmbeddingError(
                    f"Vector {index}의 차원은 {len(vector)}이며 "
                    f"필요한 차원은 {self.dimension}입니다."
                )
            if any(not math.isfinite(value) for value in vector):
                raise RemoteEmbeddingError(f"Vector {index}에 유효하지 않은 숫자가 있습니다.")
            norm = math.sqrt(sum(value * value for value in vector))
            if norm == 0:
                raise RemoteEmbeddingError(f"Vector {index}가 0 Vector입니다.")
            vectors.append([value / norm for value in vector])
        return vectors

    def _validate_configuration(self) -> None:
        if not self.base_url or not self.api_key:
            raise RemoteEmbeddingError(
                "EMBEDDING_REMOTE_BASE_URL과 EMBEDDING_API_KEY를 설정해야 합니다."
            )
        if not self.model or not self.name:
            raise RemoteEmbeddingError("원격 Embedding 모델 ID가 비어 있습니다.")
        if self.dimension != 1024:
            raise RemoteEmbeddingError("Jina/BGE 원격 Vector는 1024차원이어야 합니다.")
