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

const messageOf = (error: unknown) => error instanceof Error ? error.message : '문서 분석 테스트에 실패했습니다.';
const INITIAL_PROGRESS: OcrProgressUpdate = { stage: 'idle', progress: 0, message: '분석 대기 중' };
const isAbortError = (error: unknown) => error instanceof Error && error.name === 'AbortError';

export function useOcrTest() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [result, setResult] = useState<OcrDocumentResult | null>(null);
  const [error, setError] = useState('');
  const [saveStatus, setSaveStatus] = useState<AsyncStatus>('idle');
  const [saveMessage, setSaveMessage] = useState('');
  const [progress, setProgress] = useState<OcrProgressUpdate>(INITIAL_PROGRESS);
  const [chunkSize, setChunkSize] = useState<OcrChunkSize>(OCR_CHUNK_SIZE);
  const [overlapPercent, setOverlapPercent] = useState<OcrOverlapPercent>(OCR_OVERLAP_PERCENT);
  const analyzeController = useRef<AbortController | null>(null);
  const overlap = getOcrOverlap(chunkSize, overlapPercent);

  useEffect(() => () => analyzeController.current?.abort(), []);

  function selectFile(nextFile: File) {
    analyzeController.current?.abort();
    setFile(nextFile); setResult(null); setError(''); setSaveMessage('');
    setStatus('idle'); setSaveStatus('idle'); setProgress(INITIAL_PROGRESS);
  }

  function removeFile() {
    analyzeController.current?.abort();
    setFile(null); setResult(null); setError(''); setSaveMessage('');
    setStatus('idle'); setSaveStatus('idle'); setProgress(INITIAL_PROGRESS);
  }

  async function analyze() {
    if (!file || status === 'loading') return;
    const controller = new AbortController();
    analyzeController.current = controller;
    setStatus('loading'); setResult(null); setError(''); setSaveMessage('');
    setProgress({ stage: 'uploading', progress: 0, message: '문서를 업로드하고 있습니다.' });
    try {
      setResult(await adminAiService.analyzeDocument(
        { file, chunkSize, overlap, signal: controller.signal },
        setProgress,
      ));
      setProgress({ stage: 'completed', progress: 100, message: 'OCR 문서 분석이 완료되었습니다.' });
      setStatus('success');
    } catch (unknownError) {
      if (isAbortError(unknownError)) return;
      setError(messageOf(unknownError)); setStatus('error');
    } finally {
      if (analyzeController.current === controller) analyzeController.current = null;
    }
  }

  async function save() {
    if (!result || saveStatus === 'loading') return;
    setSaveStatus('loading'); setSaveMessage('');
    try {
      const response = await adminAiService.saveDocument({ documentName: result.documentName });
      setSaveMessage(response.message); setSaveStatus('success');
    } catch (unknownError) {
      setSaveMessage(messageOf(unknownError)); setSaveStatus('error');
    }
  }

  return {
    file,
    status,
    result,
    error,
    progress,
    saveStatus,
    saveMessage,
    chunkSize,
    overlap,
    overlapPercent,
    canAnalyze: Boolean(file) && status !== 'loading',
    selectFile,
    removeFile,
    setChunkSize,
    setOverlapPercent,
    analyze,
    save,
  };
}
