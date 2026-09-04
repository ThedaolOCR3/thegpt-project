from uuid import UUID

from sqlalchemy.orm import Session

from ai.consultation import ConsultationResult
from app.models.generated import ConsultationLogs


class ConsultationLogRepository:
    """관리자 대시보드 지표(모델별 성공률, 폴백 비율, RAG 0건 비율 등)의 데이터
    원천을 쌓기만 하는 저장소 — 조회/집계 쿼리는 대시보드 쪽에서 별도로 만든다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        result: ConsultationResult,
    ) -> ConsultationLogs:
        log = ConsultationLogs(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            model_id=result.model_id,
            provider_key=result.provider_key,
            is_fallback=result.is_fallback,
            is_emergency=result.is_emergency,
            department=result.department,
            confidence=result.confidence,
            rag_hit_count=result.rag_hit_count,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            response_time_ms=result.response_time_ms,
            error_type=result.error_type,
            finish_reason=result.finish_reason,
        )
        self.db.add(log)
        self.db.commit()
        return log
