import { MODEL_OPTIONS } from "../../../components/Chat/modelOptions";
import type { LlmModelDefinition } from "../types/llm";

export const OCR_CHUNK_SIZE_OPTIONS = [256, 512, 1024, 2048] as const;
export type OcrChunkSize = (typeof OCR_CHUNK_SIZE_OPTIONS)[number];

export const OCR_OVERLAP_PERCENT_OPTIONS = [0, 10, 15, 20] as const;
export type OcrOverlapPercent = (typeof OCR_OVERLAP_PERCENT_OPTIONS)[number];

const OCR_OVERLAP_PRESETS = {
  256: { 0: 0, 10: 25, 15: 40, 20: 50 },
  512: { 0: 0, 10: 50, 15: 75, 20: 100 },
  1024: { 0: 0, 10: 100, 15: 150, 20: 200 },
  2048: { 0: 0, 10: 200, 15: 300, 20: 400 },
} as const satisfies Record<
  OcrChunkSize,
  Record<OcrOverlapPercent, number>
>;

export const OCR_CHUNK_SIZE: OcrChunkSize = 512;
export const OCR_OVERLAP_PERCENT: OcrOverlapPercent = 10;

export function getOcrOverlap(
  chunkSize: OcrChunkSize,
  percentage: OcrOverlapPercent,
) {
  return OCR_OVERLAP_PRESETS[chunkSize][percentage];
}

export const OCR_OVERLAP = getOcrOverlap(
  OCR_CHUNK_SIZE,
  OCR_OVERLAP_PERCENT,
);
export const OCR_ACCEPT = ".pdf,.png,.jpg,.jpeg,.docx,.pptx";
export const OCR_SUPPORTED_EXTENSIONS = new Set([
  "pdf",
  "png",
  "jpg",
  "jpeg",
  "docx",
  "pptx",
]);
export const MAIN_LLM_COMPARISON_MODELS = [
  {
    id: "main-fine-tuned",
    label: "Main Model",
    family: "프로젝트 메인 모델 계열",
    trainingStage: "학습 + 파인튜닝 완료",
    description: "전체 학습 과정을 마친 운영 후보 모델입니다.",
    group: "main",
  },
  {
    id: "main-partial",
    label: "Comparison Model",
    family: "프로젝트 메인 모델 계열",
    trainingStage: "일부 데이터 학습",
    description: "동일 계열에서 학습 정도를 낮춘 비교 기준 모델입니다.",
    group: "main",
  },
] as const satisfies readonly LlmModelDefinition[];

export const OTHER_LLM_COMPARISON_MODELS = MODEL_OPTIONS.map(
  (model): LlmModelDefinition => ({
    id: model.id,
    label: model.label,
    family: "외부 비교 모델",
    trainingStage: "기본·부분 학습 비교군",
    description:
      model.id === "llama"
        ? "오류 상태 확인을 포함한 Mock 비교 모델입니다."
        : "메인 모델과 응답 특성을 비교하는 Mock 모델입니다.",
    group: "other",
  }),
);

export const LLM_COMPARISON_MODELS: readonly LlmModelDefinition[] = [
  ...MAIN_LLM_COMPARISON_MODELS,
  ...OTHER_LLM_COMPARISON_MODELS,
];

export const LLM_COMPARISON_MODEL_IDS = LLM_COMPARISON_MODELS.map(
  (model) => model.id,
);
