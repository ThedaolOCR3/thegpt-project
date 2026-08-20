export type LlmModelGroup = "main" | "other";

export type LlmRunStatus =
  | "idle"
  | "running"
  | "success"
  | "error"
  | "cancelled";

export type LlmModelDefinition = {
  id: string;
  label: string;
  family: string;
  trainingStage: string;
  description: string;
  group: LlmModelGroup;
};

export type RunLlmModelRequest = {
  prompt: string;
  modelId: string;
  file?: File;
  signal?: AbortSignal;
};

export type LlmModelResult = {
  modelId: string;
  answer: string;
  responseTimeSeconds: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
};

export type LlmModelRun = {
  modelId: string;
  status: LlmRunStatus;
  answer?: string;
  error?: string;
  responseTimeSeconds?: number;
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
  startedAt?: number;
};

export type LlmModelRunMap = Record<string, LlmModelRun>;
