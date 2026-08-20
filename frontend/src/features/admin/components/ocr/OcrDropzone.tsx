import { useRef, useState, type DragEvent } from "react";
import { UploadCloud } from "lucide-react";
import { OCR_ACCEPT } from "../../constants/adminOptions";

export function OcrDropzone({
  disabled,
  onSelect,
}: {
  disabled: boolean;
  onSelect: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) onSelect(file);
  }
  return (
    <div
      className={`file-dropzone ${dragging ? "is-dragging" : ""}`}
      onDragEnter={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={() => setDragging(false)}
      onDrop={drop}
    >
      <UploadCloud aria-hidden="true" size={32} />
      <strong>문서를 끌어 놓거나 직접 선택하세요</strong>
      <span>PDF, PNG, JPG </span>
      <button
        className="admin-secondary-button"
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        파일 선택
      </button>
      <input
        ref={inputRef}
        className="admin-visually-hidden"
        type="file"
        accept={OCR_ACCEPT}
        aria-label="OCR 테스트 파일 선택"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onSelect(file);
          event.target.value = "";
        }}
      />
    </div>
  );
}
