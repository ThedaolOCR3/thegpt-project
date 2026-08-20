import { useEffect, useState } from "react";

const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg"]);
const OFFICE_EXTENSIONS = new Set(["docx", "pptx"]);

const extensionOf = (fileName: string) =>
  fileName.split(".").pop()?.toLowerCase() ?? "";

export function OcrFilePreview({ file }: { file: File }) {
  const [preview, setPreview] = useState<{ file: File; url: string } | null>(
    null,
  );
  const extension = extensionOf(file.name);
  const isPdf = file.type === "application/pdf" || extension === "pdf";
  const isImage =
    file.type.startsWith("image/") || IMAGE_EXTENSIONS.has(extension);
  const isOffice = OFFICE_EXTENSIONS.has(extension);
  const previewUrl = preview?.file === file ? preview.url : "";

  useEffect(() => {
    if (isOffice) {
      setPreview(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreview({ file, url: objectUrl });

    return () => URL.revokeObjectURL(objectUrl);
  }, [file, isOffice]);

  if (!isPdf && !isImage && !isOffice) return null;

  if (isOffice) {
    return (
      <section className="ocr-file-preview" aria-label={`${file.name} 변환 안내`}>
        <div className="ocr-preview-header">
          <strong>파일 미리보기</strong>
        </div>
        <div className="ocr-preview-loading">
          분석 시 {extension.toUpperCase()} 문서를 PDF로 변환해 처리합니다.
        </div>
      </section>
    );
  }

  return (
    <section
      className="ocr-file-preview"
      aria-label={`${file.name} 미리보기`}
    >
      <div className="ocr-preview-header">
        <strong>파일 미리보기</strong>
        {isPdf && previewUrl && (
          <a href={previewUrl} target="_blank" rel="noreferrer">
            새 탭에서 열기
          </a>
        )}
      </div>
      {!previewUrl ? (
        <div className="ocr-preview-loading">미리보기를 준비하는 중...</div>
      ) : isPdf ? (
        <object
          className="ocr-pdf-preview"
          data={previewUrl}
          type="application/pdf"
          aria-label={`${file.name} PDF 미리보기`}
        >
          <p className="ocr-preview-fallback">
            이 브라우저에서는 PDF를 바로 표시할 수 없습니다.{" "}
            <a href={previewUrl} download={file.name}>
              PDF 다운로드
            </a>
          </p>
        </object>
      ) : (
        <img
          className="ocr-image-preview"
          src={previewUrl}
          alt={`${file.name} 미리보기`}
        />
      )}
    </section>
  );
}
