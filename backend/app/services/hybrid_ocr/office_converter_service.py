"""DOCX/PPTX를 기존 Hybrid PDF 처리에 연결할 PDF 변환 계층입니다."""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from app.services.hybrid_ocr.errors import OfficeConversionError
from app.services.hybrid_ocr.models import ValidatedDocument

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConvertedOfficeDocument:
    """LibreOffice 변환이 끝난 PDF와 사용자 검토용 경고입니다."""

    content: bytes
    warnings: list[str]


class OfficeDocumentConverter(Protocol):
    """중심 서비스가 구체적인 Office 변환 도구를 알지 않게 하는 계약입니다."""

    def convert_to_pdf(self, document: ValidatedDocument) -> ConvertedOfficeDocument: ...


class LibreOfficeDocumentConverter:
    """격리된 임시 프로필에서 LibreOffice headless 변환을 실행합니다."""

    def __init__(
        self,
        executable: str,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def convert_to_pdf(self, document: ValidatedDocument) -> ConvertedOfficeDocument:
        executable = self._resolve_executable()
        suffix = Path(document.file_name).suffix.lower()

        with TemporaryDirectory(prefix="ocr-office-") as temp_directory:
            work_directory = Path(temp_directory)
            input_directory = work_directory / "input"
            output_directory = work_directory / "output"
            profile_directory = work_directory / "profile"
            input_directory.mkdir()
            output_directory.mkdir()
            profile_directory.mkdir()

            source_path = input_directory / f"source{suffix}"
            source_path.write_bytes(document.content)
            command = [
                executable,
                f"-env:UserInstallation={profile_directory.resolve().as_uri()}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_directory),
                str(source_path),
            ]
            environment = {**os.environ, "SAL_USE_VCLPLUGIN": "gen"}

            logger.info("Office PDF 변환 시작: filename=%s", document.file_name)
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                raise OfficeConversionError(
                    f"Office 문서 변환이 {self.timeout_seconds}초 안에 완료되지 않았습니다."
                ) from exc
            except OSError as exc:
                raise OfficeConversionError(
                    "Office 문서 변환기를 실행하지 못했습니다."
                ) from exc

            converted_path = output_directory / "source.pdf"
            if completed.returncode != 0 or not converted_path.is_file():
                detail = (completed.stderr or completed.stdout or "").strip()[:500]
                logger.warning(
                    "Office PDF 변환 실패: filename=%s, returncode=%d, detail=%s",
                    document.file_name,
                    completed.returncode,
                    detail,
                )
                raise OfficeConversionError(
                    "DOCX/PPTX를 PDF로 변환하지 못했습니다. 문서 손상 여부를 확인해 주세요."
                )

            converted_content = converted_path.read_bytes()
            if not converted_content:
                raise OfficeConversionError("Office 문서 변환 결과가 비어 있습니다.")
            if len(converted_content) > self.max_output_bytes:
                max_size_mb = self.max_output_bytes // (1024 * 1024)
                raise OfficeConversionError(
                    f"변환된 PDF 크기는 {max_size_mb}MB 이하여야 합니다."
                )

            logger.info(
                "Office PDF 변환 완료: filename=%s, bytes=%d",
                document.file_name,
                len(converted_content),
            )
            return ConvertedOfficeDocument(
                content=converted_content,
                warnings=[
                    f"{suffix.removeprefix('.').upper()} 문서를 PDF로 변환해 분석했습니다.",
                    "원본 Office 프로그램과 글꼴·도형 배치가 일부 다를 수 있습니다.",
                ],
            )

    def _resolve_executable(self) -> str:
        configured_path = Path(self.executable)
        if configured_path.is_file():
            return str(configured_path)

        resolved = shutil.which(self.executable)
        if resolved:
            return resolved

        raise OfficeConversionError(
            "LibreOffice를 찾을 수 없어 DOCX/PPTX를 분석할 수 없습니다."
        )
