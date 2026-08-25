from pydantic import BaseModel


class LlmModelResponse(BaseModel):
    model_id: str
    label: str
    description: str


class LlmMessageInput(BaseModel):
    role: str
    content: str


class LlmGenerateRequest(BaseModel):
    model_id: str
    messages: list[LlmMessageInput]


class LlmGenerateResponse(BaseModel):
    model_id: str
    content: str


class LlmCompareRequest(BaseModel):
    model_ids: list[str]
    messages: list[LlmMessageInput]


class LlmCompareResult(BaseModel):
    model_id: str
    content: str | None = None
    error: str | None = None
