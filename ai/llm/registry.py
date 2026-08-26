"""사용 가능한 MedGemma LoRA 어댑터 목록.

관리자 페이지의 모델 비교, 채팅의 모델 선택 드롭다운이 둘 다 이 레지스트리를
단일 소스로 참조한다 — 어댑터를 새로 학습해서 추가할 땐 이 리스트에 한 줄만
추가하면 된다(base model은 전부 동일해서 engine.py가 자동으로 로드/스위칭한다).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelEntry:
    model_id: str
    adapter_repo: str
    label: str
    description: str


MODEL_REGISTRY: list[ModelEntry] = [
    ModelEntry(
        model_id="medgemma-screening",
        adapter_repo="gon-0130/medgemma-4b-lora-consultation-v2",
        label="MedGemma (스크리닝)",
        description="무료 Colab에서 학습한 초기 버전 — KorMedMCQA + GenMedGPT-5k-ko 2종.",
    ),
    ModelEntry(
        model_id="medgemma-main",
        adapter_repo="gon-0130/medgemma-4b-lora-consultation-main-v2",
        label="MedGemma (메인)",
        description="유료 Colab에서 학습한 메인 버전 — 지식/추론보강/대화형 11개 데이터셋.",
    ),
    # 팀원이 1~2개 데이터셋으로 학습시킨 어댑터도 여기 추가하면 관리자 비교/채팅
    # 선택지에 자동으로 노출된다. 예:
    # ModelEntry(
    #     model_id="medgemma-<이름>",
    #     adapter_repo="<HF계정>/<adapter-repo>",
    #     label="MedGemma (<설명>)",
    #     description="<어떤 데이터셋으로 학습했는지>",
    # ),
]

DEFAULT_MODEL_ID = MODEL_REGISTRY[0].model_id


def get_model_entry(model_id: str) -> ModelEntry:
    for entry in MODEL_REGISTRY:
        if entry.model_id == model_id:
            return entry
    raise KeyError(f"등록되지 않은 model_id입니다: {model_id}")


def list_models() -> list[ModelEntry]:
    return list(MODEL_REGISTRY)
