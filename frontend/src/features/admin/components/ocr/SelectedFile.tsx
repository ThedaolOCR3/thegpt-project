import { FileText, Trash2 } from 'lucide-react';

const formatBytes = (bytes: number) => bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;

export function SelectedFile({ file, disabled, onRemove }: { file: File; disabled: boolean; onRemove: () => void }) {
  return <div className="selected-file" aria-live="polite"><span className="file-icon"><FileText size={19} /></span><div><strong>{file.name}</strong><span>{formatBytes(file.size)} · {file.type || '형식 정보 없음'}</span></div><button type="button" className="icon-button" disabled={disabled} onClick={onRemove} aria-label="선택 파일 제거"><Trash2 size={17} /></button></div>;
}
