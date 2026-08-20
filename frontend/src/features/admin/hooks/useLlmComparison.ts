import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  LLM_COMPARISON_MODEL_IDS,
  LLM_COMPARISON_MODELS,
} from "../constants/adminOptions";
import { adminAiService } from "../services/adminAiService";
import type { LlmModelRunMap } from "../types/llm";

function createInitialModelRuns(): LlmModelRunMap {
  return Object.fromEntries(
    LLM_COMPARISON_MODELS.map((model) => [
      model.id,
      { modelId: model.id, status: "idle" as const },
    ]),
  );
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useLlmComparison() {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [modelRuns, setModelRuns] = useState<LlmModelRunMap>(
    createInitialModelRuns,
  );
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [error, setError] = useState("");

  const controllersRef = useRef(new Map<string, AbortController>());
  const requestVersionsRef = useRef(new Map<string, number>());
  const allRunVersionRef = useRef(0);
  const allRunActiveRef = useRef(false);

  const hasRunningModels = useMemo(
    () => Object.values(modelRuns).some((run) => run.status === "running"),
    [modelRuns],
  );

  useEffect(
    () => () => {
      allRunVersionRef.current += 1;
      allRunActiveRef.current = false;
      controllersRef.current.forEach((controller, modelId) => {
        requestVersionsRef.current.set(
          modelId,
          (requestVersionsRef.current.get(modelId) ?? 0) + 1,
        );
        controller.abort();
      });
      controllersRef.current.clear();
    },
    [],
  );

  const executeModel = useCallback(
    async (modelId: string, runPrompt: string, referenceFile: File | null) => {
      // 같은 모델의 이전 요청이 남아 있더라도 새 요청 결과만 상태를 갱신합니다.
      controllersRef.current.get(modelId)?.abort();
      const requestVersion =
        (requestVersionsRef.current.get(modelId) ?? 0) + 1;
      requestVersionsRef.current.set(modelId, requestVersion);

      const controller = new AbortController();
      const startedAt = Date.now();
      controllersRef.current.set(modelId, controller);
      setModelRuns((current) => ({
        ...current,
        [modelId]: {
          modelId,
          status: "running",
          startedAt,
        },
      }));

      try {
        const result = await adminAiService.runLlmModel({
          prompt: runPrompt,
          modelId,
          file: referenceFile ?? undefined,
          signal: controller.signal,
        });
        if (requestVersionsRef.current.get(modelId) !== requestVersion) return;

        setModelRuns((current) => ({
          ...current,
          [modelId]: {
            modelId,
            status: "success",
            answer: result.answer,
            responseTimeSeconds: result.responseTimeSeconds,
            inputTokens: result.inputTokens,
            outputTokens: result.outputTokens,
            totalTokens: result.totalTokens,
          },
        }));
      } catch (unknownError) {
        // 취소 또는 재실행된 이전 요청의 늦은 결과가 현재 카드를 덮어쓰지 못하게 합니다.
        if (requestVersionsRef.current.get(modelId) !== requestVersion) return;

        setModelRuns((current) => ({
          ...current,
          [modelId]: {
            modelId,
            status: isAbortError(unknownError) ? "cancelled" : "error",
            error: isAbortError(unknownError)
              ? "실행이 취소되었습니다."
              : unknownError instanceof Error
                ? unknownError.message
                : "모델 실행 중 오류가 발생했습니다.",
            responseTimeSeconds: (Date.now() - startedAt) / 1_000,
          },
        }));
      } finally {
        if (requestVersionsRef.current.get(modelId) === requestVersion) {
          controllersRef.current.delete(modelId);
        }
      }
    },
    [],
  );

  const runModel = useCallback(
    async (
      modelId: string,
      sharedPrompt = prompt,
      sharedFile: File | null = file,
    ) => {
      const runPrompt = sharedPrompt.trim();
      if (!runPrompt) {
        setError("비교할 공통 질문을 입력해 주세요.");
        return;
      }

      setError("");
      await executeModel(modelId, runPrompt, sharedFile);
    },
    [executeModel, file, prompt],
  );

  const runAllModels = useCallback(async () => {
    if (allRunActiveRef.current || hasRunningModels) return;

    const runPrompt = prompt.trim();
    if (!runPrompt) {
      setError("비교할 공통 질문을 입력해 주세요.");
      return;
    }

    const allRunVersion = allRunVersionRef.current + 1;
    allRunVersionRef.current = allRunVersion;
    allRunActiveRef.current = true;
    setError("");
    setIsRunningAll(true);

    // 전체 실행도 runModel()을 병렬 호출해 모델별 완료·취소·오류를 분리합니다.
    await Promise.allSettled(
      LLM_COMPARISON_MODEL_IDS.map((modelId) =>
        runModel(modelId, runPrompt, file),
      ),
    );

    if (allRunVersionRef.current === allRunVersion) {
      allRunActiveRef.current = false;
      setIsRunningAll(false);
    }
  }, [file, hasRunningModels, prompt, runModel]);

  const cancelModel = useCallback((modelId: string) => {
    const controller = controllersRef.current.get(modelId);
    if (!controller) return;

    requestVersionsRef.current.set(
      modelId,
      (requestVersionsRef.current.get(modelId) ?? 0) + 1,
    );
    controller.abort();
    controllersRef.current.delete(modelId);
    setModelRuns((current) => {
      const running = current[modelId];
      if (!running || running.status !== "running") return current;
      return {
        ...current,
        [modelId]: {
          modelId,
          status: "cancelled",
          error: "실행이 취소되었습니다.",
          responseTimeSeconds: running.startedAt
            ? (Date.now() - running.startedAt) / 1_000
            : undefined,
        },
      };
    });
  }, []);

  const reset = useCallback(() => {
    allRunVersionRef.current += 1;
    allRunActiveRef.current = false;
    controllersRef.current.forEach((controller, modelId) => {
      requestVersionsRef.current.set(
        modelId,
        (requestVersionsRef.current.get(modelId) ?? 0) + 1,
      );
      controller.abort();
    });
    controllersRef.current.clear();

    setPrompt("");
    setFile(null);
    setModelRuns(createInitialModelRuns());
    setError("");
    setIsRunningAll(false);
  }, []);

  return {
    prompt,
    setPrompt,
    file,
    setFile,
    modelRuns,
    isRunningAll,
    hasRunningModels,
    error,
    runModel,
    runAllModels,
    cancelModel,
    reset,
  };
}
