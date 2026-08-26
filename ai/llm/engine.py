"""MedGemma base model을 한 번만 로드하고, 여러 LoRA 어댑터를 이름으로 붙였다 뗐다
하며 재사용하는 엔진. base model을 등록된 어댑터 개수만큼 중복 로드하지 않는다 —
관리자 페이지의 "여러 모델 비교"와 채팅의 "모델 선택"이 이 엔진 하나를 공유한다.

GPU가 없는 환경(로컬 개발 등)에서는 import는 되지만, 실제 로드를 시도하는 시점에
명확한 RuntimeError를 낸다 — 조용히 실패하거나 CPU로 느리게 로드를 시도하지 않는다.
"""

from __future__ import annotations

import logging
import threading

from ai.llm.registry import get_model_entry

logger = logging.getLogger(__name__)

BASE_MODEL_ID = "google/medgemma-4b-it"

# 학습 노트북에서 검증된 반복 생성 방지 디코딩 설정 — 그리디 디코딩이 짧고 정형화된
# 학습 타깃 패턴에 갇혀서 같은 토큰을 반복하는 문제("두두두...")를 완화한다.
DEFAULT_GENERATION_KWARGS = {
    "max_new_tokens": 400,
    "do_sample": True,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.3,
    "no_repeat_ngram_size": 3,
}


class MedGemmaEngine:
    """base model 하나 + 어댑터 여러 개를 관리한다. 직접 생성하지 말고 get_engine()을
    통해서만 써서, 프로세스 전체에서 인스턴스가 하나로 유지되게 한다."""

    def __init__(self, hf_token: str | None = None) -> None:
        self._hf_token = hf_token
        self._model = None
        self._tokenizer = None
        self._loaded_adapters: set[str] = set()
        self._lock = threading.Lock()

    def _ensure_base_loaded(self) -> None:
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:  # 락 대기 중 다른 스레드가 이미 로드했을 수 있음
                return

            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            except ImportError as exc:
                raise RuntimeError(
                    "ai/llm 실행에 필요한 패키지가 설치되지 않았습니다 — "
                    "ai/llm/requirements.txt를 설치하세요."
                ) from exc

            if not torch.cuda.is_available():
                raise RuntimeError(
                    "GPU가 없는 환경입니다 — 4bit 양자화 로딩은 CUDA GPU가 필요합니다. "
                    "GPU가 있는 서버/런타임에서 실행하세요."
                )

            major, _ = torch.cuda.get_device_capability(0)
            compute_dtype = torch.bfloat16 if major >= 8 else torch.float16
            logger.info("MedGemma base model 로드 시작: %s (dtype=%s)", BASE_MODEL_ID, compute_dtype)

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=compute_dtype,
                bnb_4bit_use_double_quant=True,
            )

            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, token=self._hf_token)
            tokenizer.padding_side = "right"
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_ID,
                quantization_config=bnb_config,
                device_map="auto",
                dtype=compute_dtype,
                token=self._hf_token,
            )
            model.eval()

            self._tokenizer = tokenizer
            self._model = model
            logger.info("MedGemma base model 로드 완료")

    def _ensure_adapter_loaded(self, model_id: str) -> None:
        from peft import PeftModel

        entry = get_model_entry(model_id)  # 등록 안 된 model_id면 여기서 KeyError
        self._ensure_base_loaded()

        if model_id in self._loaded_adapters:
            return

        with self._lock:
            if model_id in self._loaded_adapters:
                return
            logger.info("어댑터 로드: %s (%s)", model_id, entry.adapter_repo)
            if not self._loaded_adapters:
                # 첫 어댑터는 PeftModel로 base model을 감싸야 하고, 그다음부터는
                # load_adapter로 같은 PeftModel에 이름만 다르게 추가한다.
                self._model = PeftModel.from_pretrained(
                    self._model, entry.adapter_repo, adapter_name=model_id, token=self._hf_token
                )
            else:
                self._model.load_adapter(entry.adapter_repo, adapter_name=model_id, token=self._hf_token)
            self._loaded_adapters.add(model_id)

    def generate(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        **generation_overrides,
    ) -> str:
        """messages: [{"role": "user"/"assistant", "content": "..."}] 대화 기록.
        마지막 턴은 role="user"여야 한다(그다음 assistant 응답을 생성한다)."""
        import torch

        self._ensure_adapter_loaded(model_id)
        self._model.set_adapter(model_id)

        text = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

        kwargs = {**DEFAULT_GENERATION_KWARGS, **generation_overrides}

        with torch.no_grad():
            output = self._model.generate(**inputs, **kwargs)

        response = self._tokenizer.decode(
            output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )
        return response.strip()

    def is_base_loaded(self) -> bool:
        return self._model is not None

    def loaded_adapter_ids(self) -> set[str]:
        return set(self._loaded_adapters)


_engine: MedGemmaEngine | None = None
_engine_lock = threading.Lock()


def get_engine(hf_token: str | None = None) -> MedGemmaEngine:
    """프로세스 전체에서 엔진 인스턴스를 하나만 유지한다 — 매 요청마다 base model을
    다시 로드하지 않기 위함."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = MedGemmaEngine(hf_token=hf_token)
    return _engine
