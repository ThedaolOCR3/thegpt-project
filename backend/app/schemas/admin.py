"""Hybrid OCR 응답 계약 — csj-ocr 브랜치의 schemas/admin.py에서 OCR 부분만 이식.

관리자 LLM 비교 관련 스키마(LlmCompareRequest 등)는 아직 안 가져왔다 — 지금은 채팅
첨부파일 OCR에만 hybrid_ocr을 쓰므로 필요한 만큼만 옮겼다. 나중에 관리자 대시보드
OCR/LLM 비교 화면을 붙일 때 확장하면 된다.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdminSchema(BaseModel):
    """Frontend의 camelCase와 Backend의 snake_case를 함께 허용합니다."""

    model_config = ConfigDict(populate_by_name=True)


class OcrDocumentResponse(AdminSchema):
    document_name: str = Field(alias="documentName")
    page_count: int | None = Field(alias="pageCount")
    character_count: int = Field(alias="characterCount")
    estimated_chunks: int = Field(alias="estimatedChunks")
    confidence: float
    extracted_text: str = Field(alias="extractedText")
    chunks: list[str]
    readiness: Literal["review", "ready"]
    notes: list[str]
