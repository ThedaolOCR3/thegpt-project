"""Admin·일반 LLM API·메인 채팅이 공유하는 Backend LLM 런타임입니다.

Provider 인증과 모델 매핑은 Backend 환경변수에서만 읽고, Frontend에는
Registry의 공개 ID만 노출합니다. 어드민 Facade에 런타임을 두지 않아 메인
채팅이 어드민 구현에 의존하지 않도록 합니다.
"""

from ai.llm import (
    LlmApplicationService,
    LlmModelDefinition,
    ModelRegistry,
    ProviderRegistry,
)
from ai.llm.providers.remote_http import RemoteHttpLlmProvider
from app.core.config import settings


def create_model_registry() -> ModelRegistry:
    """Backend 설정을 공통 모델 Registry로 변환합니다."""

    return ModelRegistry(
        (
            LlmModelDefinition(
                id="gemma",
                label="Gemma Medical",
                family="Gemma 2 2B",
                training_stage="한국어 의료 QLoRA",
                description="Vast.ai V100에서 실행하는 Gemma 2 2B 한국어 의료 QLoRA 모델입니다.",
                group="main",
                provider_key="remote-http",
                provider_model=settings.llm_remote_gemma_model,
            ),
            LlmModelDefinition(
                id="medgemma",
                label="MedGemma (최종)",
                family="MedGemma LoRA",
                training_stage="의료 상담 최종 LoRA",
                description="Vast.ai V100에서 MedGemma 4B base에 최종 상담 LoRA를 적용한 모델입니다.",
                group="main",
                provider_key="remote-http",
                provider_model=settings.llm_remote_medgemma_final_model,
            ),
            LlmModelDefinition(
                id="medgemma-dataset",
                label="MedGemma (데이터셋)",
                family="MedGemma LoRA",
                training_stage="의료 상담 데이터셋 LoRA",
                description="최종 모델과 같은 MedGemma 4B base에 데이터셋 LoRA를 적용한 비교 모델입니다.",
                group="main",
                provider_key="remote-http",
                provider_model=settings.llm_remote_medgemma_dataset_model,
            ),
            LlmModelDefinition(
                id="qwen",
                label="Qwen Medical",
                family="Qwen3 4B",
                training_stage="QLoRA 의료 파인튜닝",
                description="Vast.ai V100에서 실행하는 Qwen3 4B 의료 QLoRA 모델입니다.",
                group="other",
                provider_key="remote-http",
                provider_model=settings.llm_remote_qwen_model,
            ),
            LlmModelDefinition(
                id="llama",
                label="Llama Medical",
                family="Llama 3.2 3B",
                training_stage="QLoRA 의료 파인튜닝",
                description="Vast.ai V100에서 실행하는 Llama 3.2 3B 의료 QLoRA 모델입니다.",
                group="other",
                provider_key="remote-http",
                provider_model=settings.llm_remote_llama_model,
            ),
        )
    )


def create_llm_application() -> LlmApplicationService:
    providers = ProviderRegistry(
        (
            RemoteHttpLlmProvider(
                enabled=settings.llm_remote_enabled,
                base_url=settings.llm_remote_base_url,
                api_key=settings.llm_remote_api_key,
                timeout_seconds=settings.llm_remote_timeout_seconds,
                max_concurrency=settings.llm_remote_max_concurrency,
            ),
        )
    )
    return LlmApplicationService(create_model_registry(), providers)


# FastAPI 프로세스 안에서 Provider의 동시성 제어와 Registry를 공유한다.
llm_application = create_llm_application()
