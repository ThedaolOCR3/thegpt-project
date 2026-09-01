import { RefreshCw } from "lucide-react";
import { useOcrTest } from "../../hooks/useOcrTest";
import { OcrChunkSettings } from "./OcrChunkSettings";
import { OcrDropzone } from "./OcrDropzone";
import { OcrFilePreview } from "./OcrFilePreview";
import { OcrResultSummary } from "./OcrResultSummary";
import { OcrSourceSelector } from "./OcrSourceSelector";
import { OcrWebUrlInput } from "./OcrWebUrlInput";
import { SelectedFile } from "./SelectedFile";

export function OcrPanel() {
  const ocr = useOcrTest();
  return (
    <section className="admin-workspace" aria-labelledby="ocr-panel-title">
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">RAG CONTENT INGESTION</span>
          <h2 id="ocr-panel-title">RAG 자료 추출 및 등록</h2>
          <p>
            문서 파일 또는 공개 웹페이지에서 텍스트와 이미지 내용을 추출하고,
            RAG 지식으로 저장하기 전에 추출 품질과 예상 chunk 구성을 확인합니다.
          </p>
        </div>
        {/* <span className="mock-badge">프론트엔드 Mock</span> */}
      </div>
      <div className="ocr-layout">
        <div className="admin-card ocr-input-card">
          <OcrSourceSelector
            value={ocr.sourceType}
            disabled={ocr.status === "loading"}
            onChange={ocr.setSourceType}
          />
          {ocr.sourceType === "file" ? (
            <>
              <OcrDropzone
                disabled={ocr.status === "loading"}
                onSelect={ocr.selectFile}
              />
              {ocr.file ? (
                <SelectedFile
                  file={ocr.file}
                  disabled={ocr.status === "loading"}
                  onRemove={ocr.removeFile}
                />
              ) : (
                <div className="admin-empty-inline">
                  아직 선택한 문서가 없습니다.
                </div>
              )}
            </>
          ) : (
            <OcrWebUrlInput
              value={ocr.url}
              disabled={ocr.status === "loading"}
              onChange={ocr.setUrl}
            />
          )}
          <OcrChunkSettings
            chunkSize={ocr.chunkSize}
            overlap={ocr.overlap}
            overlapPercent={ocr.overlapPercent}
            disabled={ocr.status === "loading"}
            onChunkSizeChange={ocr.setChunkSize}
            onOverlapPercentChange={ocr.setOverlapPercent}
          />
          {ocr.sourceType === "file" && ocr.file && (
            <OcrFilePreview file={ocr.file} />
          )}
          {ocr.error && (
            <p className="admin-error" role="alert">
              {ocr.error}
            </p>
          )}
          <button
            className="admin-primary-button"
            type="button"
            disabled={!ocr.canAnalyze}
            onClick={ocr.analyze}
          >
            {ocr.status === "loading" ? (
              <>
                <RefreshCw className="spin" size={17} /> 분석 중...
              </>
            ) : ocr.sourceType === "file" ? (
              "문서 분석 테스트"
            ) : (
              "웹페이지 분석 테스트"
            )}
          </button>
        </div>
        <div
          className="admin-card ocr-result-card"
          aria-live="polite"
          aria-busy={ocr.status === "loading"}
        >
          <OcrResultSummary
            status={ocr.status}
            progress={ocr.progress}
            result={ocr.result}
            saveStatus={ocr.saveStatus}
            saveMessage={ocr.saveMessage}
            onSave={ocr.save}
          />
        </div>
      </div>
    </section>
  );
}
