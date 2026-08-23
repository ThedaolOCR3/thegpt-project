"""Admin OCR·Vector 저장·LLM API의 요청/응답 계약을 정의합니다."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class OcrJobCreatedResponse(AdminSchema):
    job_id: str = Field(alias="jobId")
    status: Literal["queued"]


class OcrJobStatusResponse(AdminSchema):
    job_id: str = Field(alias="jobId")
    status: Literal["queued", "processing", "completed", "failed"]
    stage: str
    progress: int = Field(ge=0, le=100)
    message: str
    result: OcrDocumentResponse | None = None
    error: str | None = None


class OcrVectorSaveRequest(AdminSchema):
    job_id: str = Field(alias="jobId", min_length=1, max_length=64)


class OcrVectorSaveResponse(AdminSchema):
    message: str
    document_id: UUID = Field(alias="documentId")
    chunk_count: int = Field(alias="chunkCount", ge=1)
    embedding_dimension: int = Field(alias="embeddingDimension")
    embedding_model: str = Field(alias="embeddingModel")


class LlmRunRequest(AdminSchema):
    prompt: str = Field(min_length=1, max_length=10_000)
    model_id: str = Field(alias="modelId", min_length=1, max_length=100)
    document_name: str | None = Field(default=None, alias="documentName", max_length=255)

    @model_validator(mode="after")
    def validate_prompt(self) -> "LlmRunRequest":
        if not self.prompt.strip():
            raise ValueError("Prompt를 입력해 주세요.")
        return self


class LlmRunResponse(AdminSchema):
    model_id: str = Field(alias="modelId")
    provider: str
    provider_model: str = Field(alias="providerModel")
    answer: str
    response_time_seconds: float = Field(alias="responseTimeSeconds")
    input_tokens: int | None = Field(alias="inputTokens")
    output_tokens: int | None = Field(alias="outputTokens")
    total_tokens: int | None = Field(alias="totalTokens")
    finish_reason: str | None = Field(default=None, alias="finishReason")
    is_mock: bool = Field(alias="isMock")


class LlmModelDefinitionResponse(AdminSchema):
    id: str
    label: str
    family: str
    training_stage: str = Field(alias="trainingStage")
    description: str
    group: Literal["main", "other"]
    provider: str
    provider_model: str = Field(alias="providerModel")
    enabled: bool
    available: bool
    availability_message: str | None = Field(alias="availabilityMessage")
    is_mock: bool = Field(alias="isMock")


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
    input_tokens: int | None = Field(alias="inputTokens")
    output_tokens: int | None = Field(alias="outputTokens")
    chunk_size: int = Field(alias="chunkSize")
    overlap: int
