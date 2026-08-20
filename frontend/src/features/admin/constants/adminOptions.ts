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
export const DEFAULT_LLM_MODEL_IDS = ["medgemma", "gemma", "qwen"];
