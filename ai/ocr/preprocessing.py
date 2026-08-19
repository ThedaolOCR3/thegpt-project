"""이미지 전처리 — OCR 정확도를 높이기 위한 노이즈 제거 + 기울기 보정."""
import cv2
import numpy as np

# 이보다 긴 변을 가진 이미지는 축소한다 — 폰 카메라 사진(4000px+)은 PaddleOCR
# 인식률에 그 이상의 해상도가 필요 없는데, denoise/deskew/추론 비용만 픽셀 수에
# 비례해서 늘어난다. 실제 문서로 확인 없이 더 줄이지는 말 것(글자가 뭉개질 수 있음).
MAX_DIMENSION = 2200

PDF_MAGIC = b"%PDF"


def is_pdf(data: bytes) -> bool:
    return data[:4] == PDF_MAGIC


def load_image(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("이미지를 디코딩하지 못했습니다.")
    return image


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[np.ndarray]:
    """PDF 각 페이지를 OCR 파이프라인이 기대하는 BGR numpy 이미지로 렌더링한다."""
    import pypdfium2 as pdfium

    scale = dpi / 72  # pdfium은 72dpi 기준 좌표계를 씀
    images: list[np.ndarray] = []
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        for page in pdf:
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil().convert("RGB")
            rgb = np.array(pil_image)
            images.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    finally:
        pdf.close()
    return images


def resize_if_too_large(image: np.ndarray, max_dimension: int = MAX_DIMENSION) -> np.ndarray:
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_dimension:
        return image
    scale = max_dimension / longest
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


def denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image, None, 6, 6, 7, 21)


def deskew(image: np.ndarray) -> np.ndarray:
    """문서가 스캔/촬영 과정에서 기울어져 있으면 회전시켜 바로잡는다.

    주의: minAreaRect를 글자 픽셀 전체에 대해 한 번에 구하는 방식은 글자가
    띄엄띄엄 떨어져 있는(문장이 짧은/여백이 많은) 이미지에서 실제 기울기와 무관한
    값을 내놓는다 — 실제로 멀쩡한 가로 텍스트를 90도 가까이 돌려버려 텍스트를
    깨뜨리는 걸 확인했다. 대신 Hough 직선 검출로 실제 '선분들'의 각도 중앙값을
    쓴다 — 텍스트 줄이 실제로 이루는 방향에 더 안정적으로 반응한다.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=image.shape[1] // 4, maxLineGap=10)
    if lines is None:
        return image

    angles = []
    for x1, y1, x2, y2 in lines[:, 0]:
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # 텍스트 줄은 수평에 가깝다고 가정 — 수직에 가까운 선(표 테두리 등)은 제외.
        if abs(angle) < 45:
            angles.append(angle)

    if not angles:
        return image

    skew = float(np.median(angles))
    if abs(skew) < 0.5:  # 거의 안 기울어졌으면 그대로 둔다 (불필요한 왜곡 방지)
        return image

    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), skew, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """이미 디코딩된 이미지에 표준 전처리를 적용: 크기 축소(필요시) -> 노이즈 제거 -> 기울기 보정."""
    image = resize_if_too_large(image)
    image = denoise(image)
    image = deskew(image)
    return image


def preprocess(image_bytes: bytes) -> np.ndarray:
    """OCR에 넣기 전 표준 전처리 순서: 디코딩 -> 크기 축소(필요시) -> 노이즈 제거 -> 기울기 보정."""
    return preprocess_image(load_image(image_bytes))
