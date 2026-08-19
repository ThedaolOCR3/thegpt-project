"""Admin OCR·LLM Mock API의 요청/응답 계약을 정의합니다."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdminSchema(BaseModel):
    """Frontend의 camelCase와 Backend의 snake_case를 함께 허용합니다."""

    model_config = ConfigDict(populate_by_name=True)


class OcrDocumentResponse(AdminSchema):
    document_name: str = Field(alias="documentName")
    page_count: int = Field(alias="pageCount")
    character_count: int = Field(alias="characterCount")
    estimated_chunks: int = Field(alias="estimatedChunks")
    confidence: float
    extracted_text: str = Field(alias="extractedText")
    chunks: list[str]
    readiness: Literal["review", "ready"]
    notes: list[str]


class VectorSaveTestRequest(AdminSchema):
    document_name: str = Field(alias="documentName", min_length=1, max_length=255)


class VectorSaveTestResponse(AdminSchema):
    message: str


class LlmCompareRequest(AdminSchema):
    prompt: str = Field(min_length=1, max_length=10_000)
    model_ids: list[str] = Field(alias="modelIds", min_length=2, max_length=4)
    document_name: str | None = Field(default=None, alias="documentName", max_length=255)
    chunk_size: int = Field(default=512, alias="chunkSize", ge=100, le=4096)
    overlap: int = Field(default=50, ge=0)

    @model_validator(mode="after")
    def validate_compare_options(self) -> "LlmCompareRequest":
        if not self.prompt.strip():
            raise ValueError("Prompt를 입력해 주세요.")
        if len(set(self.model_ids)) != len(self.model_ids):
            raise ValueError("동일한 모델을 중복해서 선택할 수 없습니다.")
        if self.overlap >= self.chunk_size:
            raise ValueError("Overlap은 Chunk Size보다 작아야 합니다.")
        return self


class LlmModelResponse(AdminSchema):
    model_id: str = Field(alias="modelId")
    status: Literal["success", "error"]
    answer: str | None = None
    error: str | None = None
    response_time_seconds: float = Field(alias="responseTimeSeconds")
    input_tokens: int = Field(alias="inputTokens")
    output_tokens: int = Field(alias="outputTokens")
    chunk_size: int = Field(alias="chunkSize")
    overlap: int
