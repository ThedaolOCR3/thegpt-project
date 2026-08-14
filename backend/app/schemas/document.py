from pydantic import BaseModel


class OcrLineResponse(BaseModel):
    text: str
    confidence: float


class OcrResponse(BaseModel):
    text: str
    lines: list[OcrLineResponse]
