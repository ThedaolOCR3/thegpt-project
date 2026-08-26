import unittest
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image

from ai.ocr.contracts import OcrDocumentInput, OcrProcessingConfig
from ai.ocr.errors import DocumentTooLargeError, DocumentValidationError
from ai.ocr.validation import validate_document


class OcrValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = OcrProcessingConfig(
            max_file_bytes=1024 * 1024,
            max_pdf_pages=5,
            native_text_min_chars=20,
            significant_image_area_ratio=0.03,
            pdf_render_dpi=100,
            max_image_side=1200,
            max_image_pixels=1_000_000,
            paddle_device="cpu",
            paddle_language="korean",
        )

    def test_valid_png_returns_framework_independent_document(self) -> None:
        validated = validate_document(
            OcrDocumentInput("sample.png", "image/png", _make_png()),
            self.config,
        )

        self.assertEqual(validated.file_type, "image")
        self.assertEqual(validated.file_name, "sample.png")

    def test_empty_file_is_rejected(self) -> None:
        with self.assertRaises(DocumentValidationError):
            validate_document(
                OcrDocumentInput("empty.png", "image/png", b""),
                self.config,
            )

    def test_file_over_limit_is_rejected(self) -> None:
        tiny_config = OcrProcessingConfig(
            **{**self.config.__dict__, "max_file_bytes": 10}
        )
        with self.assertRaises(DocumentTooLargeError):
            validate_document(
                OcrDocumentInput("large.png", "image/png", _make_png()),
                tiny_config,
            )

    def test_extension_binary_mismatch_is_rejected(self) -> None:
        with self.assertRaises(DocumentValidationError):
            validate_document(
                OcrDocumentInput("image.pdf", "application/pdf", _make_png()),
                self.config,
            )

    def test_office_path_traversal_is_rejected(self) -> None:
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "types")
            archive.writestr("_rels/.rels", "rels")
            archive.writestr("word/document.xml", "document")
            archive.writestr("../outside.txt", "unsafe")

        with self.assertRaises(DocumentValidationError):
            validate_document(
                OcrDocumentInput(
                    "unsafe.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    output.getvalue(),
                ),
                self.config,
            )


def _make_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (100, 60), "white").save(output, format="PNG")
    return output.getvalue()


if __name__ == "__main__":
    unittest.main()
