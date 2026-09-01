"""OCR 문서와 Chunk를 같은 DB Transaction으로 저장합니다."""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.generated import AdminDocuments, ChunkEmbeddings, DocumentChunks
from app.repositories.document_chunk import pad_embedding

logger = logging.getLogger(__name__)


class DocumentPersistenceError(Exception):
    """문서 또는 Chunk 저장 Transaction이 실패했을 때 발생합니다."""


@dataclass(frozen=True)
class SavedDocument:
    document_id: UUID
    chunk_count: int


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_with_chunks(
        self,
        *,
        original_file_url: str,
        extracted_text: str,
        chunks: list[str],
        embeddings_by_provider: dict[str, list[list[float]]],
    ) -> SavedDocument:
        """문서·Chunk·Provider별 Vector를 하나의 Transaction으로 저장합니다."""

        if not embeddings_by_provider:
            raise DocumentPersistenceError("저장할 Embedding Provider가 없습니다.")
        if any(len(chunks) != len(vectors) for vectors in embeddings_by_provider.values()):
            raise DocumentPersistenceError("Chunk와 Provider별 Embedding 개수가 일치하지 않습니다.")

        try:
            document = AdminDocuments(
                original_file_url=original_file_url,
                ocr_extracted_text=extracted_text,
                ocr_status="completed",
            )
            self.db.add(document)
            # DB가 생성하는 UUID를 모든 Chunk의 FK에 사용하기 위해 먼저 flush합니다.
            self.db.flush()
            if document.id is None:
                raise DocumentPersistenceError("저장된 문서 ID를 확인할 수 없습니다.")

            rows = [
                DocumentChunks(
                    document_id=document.id,
                    chunk_index=index,
                    chunk_text=chunk,
                )
                for index, chunk in enumerate(chunks)
            ]
            self.db.add_all(rows)
            # Chunk UUID를 chunk_embeddings FK로 사용하기 위해 같은 Transaction에서 flush합니다.
            self.db.flush()
            embedding_rows = [
                ChunkEmbeddings(
                    chunk_id=chunk.id,
                    provider_name=provider_name,
                    dimension=len(vector),
                    embedding=pad_embedding(vector),
                )
                for provider_name, vectors in embeddings_by_provider.items()
                for chunk, vector in zip(rows, vectors, strict=True)
            ]
            self.db.add_all(embedding_rows)
            self.db.commit()
            logger.info(
                "[OCR SAVE] neon insert complete: document_id=%s chunks=%d providers=%s",
                document.id,
                len(rows),
                list(embeddings_by_provider),
            )
            return SavedDocument(document_id=document.id, chunk_count=len(rows))
        except DocumentPersistenceError:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.exception("[OCR SAVE] Neon transaction rollback")
            raise DocumentPersistenceError("Neon DB에 OCR 문서를 저장하지 못했습니다.") from exc

    def begin_staged_save(self, *, original_file_url: str, extracted_text: str) -> UUID:
        """대용량 Chunk 배치 저장을 시작하고 검색 비노출 상태로 문서를 생성합니다."""

        try:
            document = AdminDocuments(
                original_file_url=original_file_url,
                ocr_extracted_text=extracted_text,
                ocr_status="processing",
            )
            self.db.add(document)
            self.db.flush()
            if document.id is None:
                raise DocumentPersistenceError("저장된 문서 ID를 확인할 수 없습니다.")
            self.db.commit()
            return document.id
        except DocumentPersistenceError:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise DocumentPersistenceError("Neon DB에 OCR 문서를 생성하지 못했습니다.") from exc

    def append_staged_chunks(
        self,
        *,
        document_id: UUID,
        start_index: int,
        chunks: list[str],
        embeddings_by_provider: dict[str, list[list[float]]],
    ) -> None:
        if not embeddings_by_provider or any(
            len(chunks) != len(vectors) for vectors in embeddings_by_provider.values()
        ):
            raise DocumentPersistenceError("Chunk와 Provider별 Embedding 개수가 일치하지 않습니다.")
        try:
            rows = [
                DocumentChunks(
                    document_id=document_id,
                    chunk_index=start_index + index,
                    chunk_text=chunk,
                )
                for index, chunk in enumerate(chunks)
            ]
            self.db.add_all(rows)
            self.db.flush()
            self.db.add_all(
                [
                    ChunkEmbeddings(
                        chunk_id=chunk.id,
                        provider_name=provider_name,
                        dimension=len(vector),
                        embedding=pad_embedding(vector),
                    )
                    for provider_name, vectors in embeddings_by_provider.items()
                    for chunk, vector in zip(rows, vectors, strict=True)
                ]
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DocumentPersistenceError("Neon DB에 OCR Chunk 배치를 저장하지 못했습니다.") from exc

    def finish_staged_save(self, document_id: UUID, chunk_count: int) -> SavedDocument:
        try:
            document = self.db.get(AdminDocuments, document_id)
            if document is None:
                raise DocumentPersistenceError("저장 중인 OCR 문서를 찾을 수 없습니다.")
            document.ocr_status = "completed"
            self.db.commit()
            return SavedDocument(document_id=document_id, chunk_count=chunk_count)
        except DocumentPersistenceError:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise DocumentPersistenceError("OCR 문서 저장을 완료하지 못했습니다.") from exc

    def abort_staged_save(self, document_id: UUID) -> None:
        try:
            self.db.query(AdminDocuments).filter(AdminDocuments.id == document_id).delete()
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise DocumentPersistenceError("실패한 OCR 문서를 정리하지 못했습니다.") from exc
