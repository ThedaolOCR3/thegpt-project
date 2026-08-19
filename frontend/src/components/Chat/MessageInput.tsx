import { useRef, useState, type FormEvent } from 'react';
import { Loader2, Plus, Send, X } from 'lucide-react';
import { ModelSelect } from './ModelSelect';

// .dcm/.dicom(DICOM)은 확장자만으로도 의료 영상임을 신뢰성 있게 판별할 수 있어 업로드 자체를 막는다.
// 반면 일반 png/jpg 등은 확장자만으로 "이게 MRI/CT/X-Ray 사진인지, 그냥 사진인지" 구분이 불가능하다
// (X-Ray를 촬영해서 jpg로 내보내는 경우도 흔함). 그래서 이쪽은 업로드는 허용하되 경고만 보여준다.
// 실제로 MRI/CT/X-Ray 여부를 검증하려면 백엔드에서 이미지 내용을 보는 분류 모델이 필요하다 — 지금은 mock 단계.
const BLOCKED_EXTENSIONS = ['dcm', 'dicom'];
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff'];

function getExtension(file: File) {
  return file.name.split('.').pop()?.toLowerCase() ?? '';
}

function isBlockedFile(file: File) {
  return BLOCKED_EXTENSIONS.includes(getExtension(file));
}

function isImageFile(file: File) {
  return IMAGE_EXTENSIONS.includes(getExtension(file)) || file.type.startsWith('image/');
}

type MessageInputProps = {
  onSend: (content: string, files: File[]) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function MessageInput({ onSend, disabled, placeholder = '메시지를 입력하세요' }: MessageInputProps) {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [imageWarning, setImageWarning] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFilesSelected(selected: FileList | null) {
    if (!selected || selected.length === 0) return;

    const accepted: File[] = [];
    let hasSoftWarning = false;

    for (const file of Array.from(selected)) {
      if (isBlockedFile(file)) {
        continue; // DICOM 등은 아예 첨부 목록에 넣지 않음
      }
      if (isImageFile(file)) {
        hasSoftWarning = true;
      }
      accepted.push(file);
    }

    setImageWarning(hasSoftWarning);
    if (accepted.length > 0) setFiles((current) => [...current, ...accepted]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function removeFile(index: number) {
    setFiles((current) => current.filter((_, i) => i !== index));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed && files.length === 0) return;
    if (disabled) return;

    onSend(trimmed, files);
    setText('');
    setFiles([]);
    setImageWarning(false);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      {imageWarning && (
        <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
          이미지는 첨부되지만, MRI·CT·X-Ray 등 의료 영상은 아직 분석할 수 없어 해당 부분은 제외하고
          답변이 생성돼요. 증상은 최대한 글로 함께 적어주시면 더 정확한 답변을 드릴 수 있어요.
        </div>
      )}

      {files.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {files.map((file, index) => (
            <span
              key={`${file.name}-${index}`}
              className="flex items-center gap-1 rounded-full bg-neutral-100 px-2.5 py-1 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
            >
              {file.name}
              <button
                type="button"
                title={`${file.name} 첨부 취소`}
                aria-label={`${file.name} 첨부 취소`}
                onClick={() => removeFile(index)}
                className="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200"
              >
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Claude 검색창 참고 레이아웃: 위쪽은 텍스트 입력 전용 줄, 아래쪽이 도구 모음 줄 */}
      <div className="flex flex-col gap-2.5 rounded-3xl border border-neutral-200 bg-white px-4 py-3 shadow-sm dark:border-neutral-700 dark:bg-neutral-900">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder={disabled ? '전송 중이에요...' : placeholder}
          rows={1}
          className="max-h-32 w-full resize-none bg-transparent text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none dark:text-neutral-100 dark:placeholder:text-neutral-500"
        />

        <div className="flex items-center justify-between">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFilesSelected(e.target.files)}
          />
          <button
            type="button"
            title="파일 첨부"
            aria-label="파일 첨부"
            onClick={() => fileInputRef.current?.click()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-white/10 dark:hover:text-neutral-200"
          >
            <Plus size={18} />
          </button>

          <div className="flex items-center gap-1">
            <ModelSelect />
            <button
              type="submit"
              disabled={disabled || (!text.trim() && files.length === 0)}
              title="메시지 보내기"
              aria-label="메시지 보내기"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white disabled:bg-neutral-200 disabled:text-neutral-400 dark:disabled:bg-neutral-800 dark:disabled:text-neutral-600"
            >
              {disabled ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
