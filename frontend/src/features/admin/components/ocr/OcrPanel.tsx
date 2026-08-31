import { CheckCircle2, Database, RefreshCw } from "lucide-react";
import { useOcrTest } from "../../hooks/useOcrTest";
import { OcrChunkSettings } from "./OcrChunkSettings";
import { OcrDropzone } from "./OcrDropzone";
import { OcrFilePreview } from "./OcrFilePreview";
import { OcrResultSummary } from "./OcrResultSummary";
import { SelectedFile } from "./SelectedFile";

export function OcrPanel() {
  const ocr = useOcrTest();
  const saveStatus = ocr.activeItem?.saveStatus ?? "idle";
  const saveMessage = ocr.activeItem?.saveMessage ?? "";

  return (
    <section className="admin-workspace" aria-labelledby="ocr-panel-title">
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">RAG DOCUMENT LAB</span>
          <h2 id="ocr-panel-title">문서 OCR 준비 테스트</h2>
          <p>
            문서가 RAG 지식으로 등록되기 전에 추출 품질과 예상 chunk 구성을
            확인합니다.
          </p>
        </div>
        {/* <span className="mock-badge">프론트엔드 Mock</span> */}
      </div>
      <div className="ocr-layout">
        <div className="admin-card ocr-input-card">
          <OcrDropzone
            disabled={ocr.isBusy}
            onSelect={ocr.selectFiles}
          />
          {ocr.items.length > 0 ? (
            <div className="selected-file-list">
              {ocr.items.map((item) => (
                <SelectedFile
                  key={item.id}
                  file={item.file}
                  selected={item.id === ocr.activeItem?.id}
                  status={item.status}
                  progress={item.progress}
                  disabled={ocr.isBusy}
                  onSelect={() => ocr.setActiveId(item.id)}
                  onRemove={() => ocr.removeFile(item.id)}
                />
              ))}
            </div>
          ) : (
            <div className="admin-empty-inline">
              아직 선택한 문서가 없습니다.
            </div>
          )}
          <OcrChunkSettings
            chunkSize={ocr.chunkSize}
            overlap={ocr.overlap}
            overlapPercent={ocr.overlapPercent}
            disabled={ocr.isBusy}
            onChunkSizeChange={ocr.setChunkSize}
            onOverlapPercentChange={ocr.setOverlapPercent}
          />
          {ocr.activeItem && <OcrFilePreview file={ocr.activeItem.file} />}
          {(ocr.selectionError || ocr.activeItem?.error) && (
            <p className="admin-error" role="alert">
              {ocr.selectionError || ocr.activeItem?.error}
            </p>
          )}
          <button
            className="admin-primary-button"
            type="button"
            disabled={!ocr.canAnalyze}
            onClick={ocr.analyze}
          >
            {ocr.isLoading ? (
              <>
                <RefreshCw className="spin" size={17} /> 분석 중...
              </>
            ) : (
              `${ocr.items.length}개 문서 분석 테스트`
            )}
          </button>

          <section
            className={`ocr-save-zone ${ocr.canSave ? "is-ready" : ""} ${
              saveStatus === "success" ? "is-saved" : ""
            }`}
            aria-labelledby="ocr-save-title"
          >
            <div className="ocr-save-heading">
              <span className="ocr-save-icon">
                {saveStatus === "success" ? <CheckCircle2 size={18} /> : <Database size={18} />}
              </span>
              <div>
                <strong id="ocr-save-title">청킹 결과 벡터화 및 저장</strong>
                <span>
                  {saveStatus === "success"
                    ? "선택한 문서가 VectorDB에 저장되었습니다."
                    : ocr.activeItem?.result
                      ? "버튼을 클릭하면 Chunk를 벡터화한 뒤 VectorDB에 저장합니다."
                      : "OCR 변환과 Chunk 생성이 완료되면 저장할 수 있습니다."}
                </span>
              </div>
              {saveStatus === "success" && <span className="ocr-saved-badge">저장됨</span>}
            </div>

            <p className="ocr-save-warning">
              이 버튼을 클릭하기 전에는 변환 결과가 VectorDB에 저장되지 않습니다.
            </p>

            <button
              className="admin-primary-button ocr-save-button"
              type="button"
              onClick={() => void ocr.save()}
              disabled={!ocr.canSave}
            >
              {saveStatus === "loading" ? (
                <>
                  <RefreshCw className="spin" size={17} /> 벡터화 및 저장 중...
                </>
              ) : saveStatus === "success" ? (
                <>
                  <CheckCircle2 size={17} /> VectorDB 저장 완료
                </>
              ) : (
                <>
                  <Database size={17} /> 선택 문서 VectorDB에 저장
                </>
              )}
            </button>

            {saveMessage && (
              <p
                className={saveStatus === "error" ? "admin-error" : "admin-success"}
                role="status"
              >
                {saveMessage}
              </p>
            )}
          </section>
        </div>
        <div
          className="admin-card ocr-result-card"
          aria-live="polite"
          aria-busy={ocr.isLoading}
        >
          <OcrResultSummary
            status={ocr.activeItem?.status ?? "idle"}
            progress={ocr.activeItem?.progress ?? { stage: "idle", progress: 0, message: "분석 대기 중" }}
            result={ocr.activeItem?.result ?? null}
          />
        </div>
      </div>
    </section>
  );
}
