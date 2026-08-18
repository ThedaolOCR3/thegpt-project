import { useState } from "react";
import { DEFAULT_LLM_MODEL_IDS } from "../constants/adminOptions";
import { adminAiService } from "../services/adminAiService";
import type { AsyncStatus } from "../types/common";
import type { LlmComparisonResult } from "../types/llm";

export function useLlmComparison() {
  const [prompt, setPrompt] = useState("");
  const [modelIds, setModelIds] = useState<string[]>(DEFAULT_LLM_MODEL_IDS);
  const [file, setFile] = useState<File | null>(null);
  const [chunkSize, setChunkSize] = useState(512);
  const [overlap, setOverlap] = useState(50);
  const [status, setStatus] = useState<AsyncStatus>("idle");
  const [results, setResults] = useState<LlmComparisonResult[]>([]);
  const [error, setError] = useState("");

  function toggleModel(modelId: string) {
    setModelIds((current) =>
      current.includes(modelId)
        ? current.filter((id) => id !== modelId)
        : [...current, modelId],
    );
  }

  function validate() {
    if (!prompt.trim()) return "비교할 공통 질문을 입력해 주세요.";
    if (modelIds.length < 2) return "비교할 모델을 2개 이상 선택해 주세요.";
    if (chunkSize < 100 || chunkSize > 4096)
      return "Chunk Size는 100~4096 사이로 입력해 주세요.";
    if (overlap < 0 || overlap >= chunkSize)
      return "Overlap은 0 이상이며 Chunk Size보다 작아야 합니다.";
    return "";
  }

  async function compare() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      setStatus("error");
      return;
    }
    if (status === "loading") return;
    setError("");
    setResults([]);
    setStatus("loading");
    try {
      setResults(
        await adminAiService.compareModels({
          prompt: prompt.trim(),
          modelIds,
          file: file ?? undefined,
          chunkSize,
          overlap,
        }),
      );
      setStatus("success");
    } catch (unknownError) {
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "모델 비교 테스트에 실패했습니다.",
      );
      setStatus("error");
    }
  }

  function reset() {
    setPrompt("");
    setModelIds(DEFAULT_LLM_MODEL_IDS);
    setFile(null);
    setChunkSize(512);
    setOverlap(50);
    setResults([]);
    setError("");
    setStatus("idle");
  }

  return {
    prompt,
    setPrompt,
    modelIds,
    toggleModel,
    file,
    setFile,
    chunkSize,
    setChunkSize,
    overlap,
    setOverlap,
    status,
    results,
    error,
    compare,
    reset,
  };
}
