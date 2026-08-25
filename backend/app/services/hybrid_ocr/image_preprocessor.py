"""PaddleOCR에 전달하기 전 이미지 방향과 크기를 정리합니다."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.hybrid_ocr.errors import DocumentProcessingError


def preprocess_image(
    content: bytes,
    max_image_side: int,
    max_image_pixels: int,
) -> Image.Image:
    """EXIF 방향, 투명 배경, 과도한 해상도를 최소 범위로 보정합니다."""

    try:
        with Image.open(BytesIO(content)) as source:
            if source.width * source.height > max_image_pixels:
                raise DocumentProcessingError(
                    "OCR 대상 이미지 해상도가 허용 범위를 초과했습니다."
                )
            source.load()

            # 휴대폰 촬영 이미지의 EXIF 회전 정보를 실제 픽셀 방향에 반영합니다.
            oriented = ImageOps.exif_transpose(source)

            # 투명 배경은 OCR에서 검게 해석될 수 있어 흰색 배경과 합성합니다.
            if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                rgba_image = oriented.convert("RGBA")
                white_background = Image.new("RGBA", rgba_image.size, "white")
                white_background.alpha_composite(rgba_image)
                processed = white_background.convert("RGB")
            else:
                processed = oriented.convert("RGB")

            # 큰 이미지는 글자 형태를 유지하면서 OCR 메모리 사용량만 제한합니다.
            if max(processed.size) > max_image_side:
                processed.thumbnail(
                    (max_image_side, max_image_side),
                    Image.Resampling.LANCZOS,
                )

            return processed.copy()
    except DocumentProcessingError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DocumentProcessingError("OCR용 이미지를 준비하지 못했습니다.") from exc
