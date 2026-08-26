"""OCR 문서와 Chunk를 같은 DB Transaction으로 저장합니다."""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.generated import AdminDocuments, DocumentChunks

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
        embeddings: list[list[float]],
    ) -> SavedDocument:
        """문서와 모든 Chunk가 함께 성공하거나 모두 Rollback되도록 저장합니다."""

        if len(chunks) != len(embeddings):
            raise DocumentPersistenceError("Chunk와 Embedding 개수가 일치하지 않습니다.")

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
                    embedding=embedding,
                )
                for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            ]
            self.db.add_all(rows)
            self.db.commit()
            logger.info(
                "[OCR SAVE] neon insert complete: document_id=%s chunks=%d",
                document.id,
                len(rows),
            )
            return SavedDocument(document_id=document.id, chunk_count=len(rows))
        except DocumentPersistenceError:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.exception("[OCR SAVE] Neon transaction rollback")
            raise DocumentPersistenceError("Neon DB에 OCR 문서를 저장하지 못했습니다.") from exc
