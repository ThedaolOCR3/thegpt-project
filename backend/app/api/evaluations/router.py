from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.evaluation import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    GroundTruthParseResponse,
)
from app.services.evaluation import (
    GroundTruthTooLargeError,
    GroundTruthValidationError,
    evaluate_answers,
    parse_ground_truth_input,
)

router = APIRouter()


@router.post("/ground-truth/parse", response_model=GroundTruthParseResponse)
async def parse_ground_truth(
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> GroundTruthParseResponse:
    """정답 텍스트 또는 파일을 평가 가능한 Case 목록으로 변환합니다."""

    try:
        return await parse_ground_truth_input(text=text, file=file)
    except GroundTruthTooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except GroundTruthValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.post("/answers/run", response_model=AnswerEvaluationResponse)
def run_answer_evaluation(payload: AnswerEvaluationRequest) -> AnswerEvaluationResponse:
    """입력된 정답과 모델 답변을 항목별·평균 지표로 계산합니다."""

    return evaluate_answers(payload)
