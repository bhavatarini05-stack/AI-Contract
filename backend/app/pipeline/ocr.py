"""OCR for scanned pages using free Tesseract, with optional OpenCV preprocessing."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from functools import lru_cache

import pymupdf
from PIL import Image

from app.config import get_settings

log = logging.getLogger(__name__)

OCR_DPI = 300


@dataclass
class OcrResult:
    text: str
    confidence: float  # mean word confidence 0-100
    low_conf_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)  # line boxes


@lru_cache
def is_available() -> bool:
    try:
        import pytesseract
    except ImportError:
        return False
    cmd = get_settings().tesseract_cmd
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    elif not shutil.which("tesseract"):
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001
        return False


def render_page(pg: pymupdf.Page, dpi: int = OCR_DPI) -> Image.Image:
    pix = pg.get_pixmap(dpi=dpi)
    mode = "RGB" if pix.n < 4 else "RGBA"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples).convert("RGB")


def preprocess(image: Image.Image) -> Image.Image:
    """Grayscale → deskew → denoise → adaptive binarize. Uses OpenCV if installed."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return image.convert("L")

    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    img = _deskew(img, cv2, np)
    img = cv2.fastNlMeansDenoising(img, h=10)
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    return Image.fromarray(img)


def _deskew(gray, cv2, np):
    inv = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if angle > 45:
        angle -= 90
    if abs(angle) < 0.3 or abs(angle) > 15:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def ocr_image(image: Image.Image, langs: str = "eng") -> OcrResult:
    import pytesseract

    processed = preprocess(image)
    data = pytesseract.image_to_data(
        processed, lang=langs, output_type=pytesseract.Output.DICT, config="--psm 3"
    )
    lines: dict[tuple, list[int]] = {}
    confs: list[float] = []
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        conf = float(data["conf"][i])
        if conf >= 0:
            confs.append(conf)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(i)

    text_lines, low_boxes = [], []
    for idxs in lines.values():
        text_lines.append(" ".join(data["text"][i] for i in idxs))
        line_conf = [float(data["conf"][i]) for i in idxs if float(data["conf"][i]) >= 0]
        if line_conf and sum(line_conf) / len(line_conf) < 45:
            x0 = min(data["left"][i] for i in idxs)
            y0 = min(data["top"][i] for i in idxs)
            x1 = max(data["left"][i] + data["width"][i] for i in idxs)
            y1 = max(data["top"][i] + data["height"][i] for i in idxs)
            low_boxes.append((x0, y0, x1, y1))

    return OcrResult(
        text="\n".join(text_lines),
        confidence=sum(confs) / len(confs) if confs else 0.0,
        low_conf_boxes=low_boxes,
    )
