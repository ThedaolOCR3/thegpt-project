from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generated import ChunkEmbeddings, DocumentChunks

# 마이그레이션(03b8a4b5b62a)의 chunk_embeddings.embedding VECTOR 폭과 반드시 같아야 한다.
EMBEDDING_COLUMN_WIDTH = 2048


def _pad(vector: list[float]) -> list[float]:
    """모든 provider의 벡터를 같은 폭의 컬럼에 저장하기 위해 0으로 채운다 — 코사인
    유사도는 두 벡터를 같은 자리만큼 0으로 패딩해도 값이 바뀌지 않는다(내적/노름
    둘 다 0 기여)."""
    if len(vector) > EMBEDDING_COLUMN_WIDTH:
        raise ValueError(
            f"임베딩 차원({len(vector)})이 컬럼 폭({EMBEDDING_COLUMN_WIDTH})을 초과합니다 — "
            "마이그레이션의 EMBEDDING_COLUMN_WIDTH를 늘리거나 Matryoshka 등으로 축소하세요."
        )
    return vector + [0.0] * (EMBEDDING_COLUMN_WIDTH - len(vector))


class DocumentChunkRepository:
    """document_chunks / chunk_embeddings 저장·검색만 담당한다. 임베딩 계산(ai.rag)과
    RRF 결합은 상위 서비스 계층의 책임."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_chunks(self, document_id: UUID, rows: list[dict]) -> list[DocumentChunks]:
        """rows: {chunk_index, chunk_text} 딕셔너리 리스트. 임베딩은 별도로
        `add_embeddings()`를 호출해서 붙인다."""
        chunks = [DocumentChunks(document_id=document_id, **row) for row in rows]
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def add_embeddings(self, chunk_id: UUID, provider_name: str, dimension: int, vector: list[float]) -> None:
        self.db.add(
            ChunkEmbeddings(
                chunk_id=chunk_id,
                provider_name=provider_name,
                dimension=dimension,
                embedding=_pad(vector),
            )
        )
        self.db.commit()

    def delete_by_document(self, document_id: UUID) -> None:
        """재수집(re-ingest) 전에 같은 문서의 기존 청크를 지운다 — chunk_embeddings는
        ON DELETE CASCADE라 같이 지워진다."""
        self.db.query(DocumentChunks).filter(DocumentChunks.document_id == document_id).delete()
        self.db.commit()

    def search_by_provider(
        self, provider_name: str, query_vector: list[float], top_k: int
    ) -> list[tuple[DocumentChunks, float]]:
        """지정한 provider로 저장된 임베딩만 대상으로 코사인 거리 기준 상위 top_k를
        반환한다. 반환값은 (청크, 코사인_거리) — 거리가 작을수록 더 유사하다."""
        padded_query = _pad(query_vector)
        stmt = (
            select(DocumentChunks, ChunkEmbeddings.embedding.cosine_distance(padded_query).label("distance"))
            .join(ChunkEmbeddings, ChunkEmbeddings.chunk_id == DocumentChunks.id)
            .where(ChunkEmbeddings.provider_name == provider_name)
            .order_by("distance")
            .limit(top_k)
        )
        return [(row.DocumentChunks, row.distance) for row in self.db.execute(stmt)]

    def get_by_ids(self, chunk_ids: list[UUID]) -> dict[UUID, DocumentChunks]:
        stmt = select(DocumentChunks).where(DocumentChunks.id.in_(chunk_ids))
        return {row.id: row for row in self.db.scalars(stmt)}
