import { useState } from 'react';
import { OCR_CHUNK_SIZE, OCR_OVERLAP } from '../constants/adminOptions';
import { adminAiService } from '../services/adminAiService';
import type { AsyncStatus } from '../types/common';
import type { OcrDocumentResult } from '../types/ocr';

const messageOf = (error: unknown) => error instanceof Error ? error.message : '문서 분석 테스트에 실패했습니다.';

export function useOcrTest() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [result, setResult] = useState<OcrDocumentResult | null>(null);
  const [error, setError] = useState('');
  const [saveStatus, setSaveStatus] = useState<AsyncStatus>('idle');
  const [saveMessage, setSaveMessage] = useState('');

  function selectFile(nextFile: File) {
    setFile(nextFile); setResult(null); setError(''); setSaveMessage('');
    setStatus('idle'); setSaveStatus('idle');
  }

  function removeFile() {
    setFile(null); setResult(null); setError(''); setSaveMessage('');
    setStatus('idle'); setSaveStatus('idle');
  }

  async function analyze() {
    if (!file || status === 'loading') return;
    setStatus('loading'); setResult(null); setError(''); setSaveMessage('');
    try {
      setResult(await adminAiService.analyzeDocument({ file, chunkSize: OCR_CHUNK_SIZE, overlap: OCR_OVERLAP }));
      setStatus('success');
    } catch (unknownError) {
      setError(messageOf(unknownError)); setStatus('error');
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

  return { file, status, result, error, saveStatus, saveMessage, canAnalyze: Boolean(file) && status !== 'loading', selectFile, removeFile, analyze, save };
}
