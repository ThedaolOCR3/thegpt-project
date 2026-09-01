import { useEffect, useRef, useState } from 'react';
import {
  getOcrOverlap,
  OCR_CHUNK_SIZE,
  OCR_OVERLAP_PERCENT,
  type OcrChunkSize,
  type OcrOverlapPercent,
} from '../constants/adminOptions';
import { adminAiService } from '../services/adminAiService';
import type { AsyncStatus } from '../types/common';
import type { OcrDocumentResult, OcrProgressUpdate } from '../types/ocr';
import {
  describeFileMerge,
  getFileIdentity,
  mergeSelectedFiles,
} from '../../../utils/uploadFiles';
import { OCR_SUPPORTED_EXTENSIONS } from '../constants/adminOptions';

const messageOf = (error: unknown, fallback = '문서 분석 테스트에 실패했습니다.') =>
  error instanceof Error ? error.message : fallback;
const INITIAL_PROGRESS: OcrProgressUpdate = { stage: 'idle', progress: 0, message: '분석 대기 중' };
const isAbortError = (error: unknown) => error instanceof Error && error.name === 'AbortError';

export type OcrBatchItem = {
  id: string;
  file: File;
  status: AsyncStatus;
  result: OcrDocumentResult | null;
  error: string;
  progress: OcrProgressUpdate;
  saveStatus: AsyncStatus;
  saveMessage: string;
};

function createItem(file: File): OcrBatchItem {
  return {
    id: getFileIdentity(file),
    file,
    status: 'idle',
    result: null,
    error: '',
    progress: INITIAL_PROGRESS,
    saveStatus: 'idle',
    saveMessage: '',
  };
}

export function useOcrTest() {
  const [items, setItems] = useState<OcrBatchItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectionError, setSelectionError] = useState('');
  const [chunkSize, setChunkSize] = useState<OcrChunkSize>(OCR_CHUNK_SIZE);
  const [overlapPercent, setOverlapPercent] = useState<OcrOverlapPercent>(OCR_OVERLAP_PERCENT);
  const analyzeControllers = useRef(new Map<string, AbortController>());
  const overlap = getOcrOverlap(chunkSize, overlapPercent);
  const activeItem = items.find((item) => item.id === activeId) ?? items[0] ?? null;
  const isLoading = items.some((item) => item.status === 'loading');
  const isSaving = items.some((item) => item.saveStatus === 'loading');
  const isBusy = isLoading || isSaving;
  const canSave = Boolean(
    activeItem?.status === 'success'
    && activeItem.result
    && activeItem.saveStatus !== 'loading'
    && activeItem.saveStatus !== 'success'
    && !isBusy,
  );

  useEffect(
    () => () => analyzeControllers.current.forEach((controller) => controller.abort()),
    [],
  );

  function updateItem(id: string, update: (item: OcrBatchItem) => OcrBatchItem) {
    setItems((current) => current.map((item) => (item.id === id ? update(item) : item)));
  }

  function selectFiles(nextFiles: File[]) {
    const merged = mergeSelectedFiles(
      items.map((item) => item.file),
      nextFiles,
      OCR_SUPPORTED_EXTENSIONS,
    );
    const currentById = new Map(items.map((item) => [item.id, item]));
    const nextItems = merged.files.map(
      (file) => currentById.get(getFileIdentity(file)) ?? createItem(file),
    );
    setItems(nextItems);
    setActiveId((current) => current ?? nextItems[0]?.id ?? null);
    setSelectionError(describeFileMerge(
      merged,
      'PDF, PNG, JPG, DOCX, PPTX, JSON, JSONL, CSV, TXT',
    ));
  }

  function removeFile(id: string) {
    analyzeControllers.current.get(id)?.abort();
    analyzeControllers.current.delete(id);
    const nextItems = items.filter((item) => item.id !== id);
    setItems(nextItems);
    if (activeId === id) setActiveId(nextItems[0]?.id ?? null);
    setSelectionError('');
  }

  async function analyzeItem(item: OcrBatchItem) {
    const controller = new AbortController();
    analyzeControllers.current.set(item.id, controller);
    updateItem(item.id, (current) => ({
      ...current,
      status: 'loading',
      result: null,
      error: '',
      saveStatus: 'idle',
      saveMessage: '',
      progress: { stage: 'uploading', progress: 0, message: '문서를 업로드하고 있습니다.' },
    }));
    try {
      const result = await adminAiService.analyzeDocument(
        { file: item.file, chunkSize, overlap, signal: controller.signal },
        (progress) => updateItem(item.id, (current) => ({ ...current, progress })),
      );
      updateItem(item.id, (current) => ({
        ...current,
        result,
        status: 'success',
        progress: { stage: 'completed', progress: 100, message: 'OCR 문서 분석이 완료되었습니다.' },
      }));
    } catch (unknownError) {
      if (isAbortError(unknownError)) return;
      updateItem(item.id, (current) => ({
        ...current,
        error: messageOf(unknownError),
        status: 'error',
        progress: { ...current.progress, stage: 'failed', message: '문서 분석에 실패했습니다.' },
      }));
    } finally {
      if (analyzeControllers.current.get(item.id) === controller) {
        analyzeControllers.current.delete(item.id);
      }
    }
  }

  async function analyze() {
    if (items.length === 0 || isBusy) return;
    setSelectionError('');
    await Promise.all(items.map(analyzeItem));
  }

  async function save() {
    if (!canSave || !activeItem?.result) return;
    const itemId = activeItem.id;
    const jobId = activeItem.result.jobId;
    updateItem(itemId, (current) => ({ ...current, saveStatus: 'loading', saveMessage: '' }));
    try {
      const response = await adminAiService.saveDocument({ jobId });
      updateItem(itemId, (current) => ({
        ...current,
        saveMessage: response.message,
        saveStatus: 'success',
      }));
    } catch (unknownError) {
      updateItem(itemId, (current) => ({
        ...current,
        saveMessage: messageOf(unknownError, '문서를 VectorDB에 저장하지 못했습니다.'),
        saveStatus: 'error',
      }));
    }
  }

  return {
    items,
    activeItem,
    activeId,
    selectionError,
    isLoading,
    isSaving,
    isBusy,
    canSave,
    chunkSize,
    overlap,
    overlapPercent,
    canAnalyze: items.length > 0 && !isBusy,
    selectFiles,
    removeFile,
    setActiveId,
    setChunkSize,
    setOverlapPercent,
    analyze,
    save,
  };
}
