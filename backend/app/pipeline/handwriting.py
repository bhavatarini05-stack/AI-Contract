"""Handwriting recognition with the free, local TrOCR model (Hugging Face).

Optional: install with `pip install -e ".[vision]"`. The model (~1.3 GB) downloads
once into the Hugging Face cache. Results are always flagged for human review.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from PIL import Image

log = logging.getLogger(__name__)

MODEL_NAME = "microsoft/trocr-base-handwritten"
MAX_REGIONS = 20


@lru_cache
def is_available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache
def _load():
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
    model.eval()
    return processor, model


def read_line(image: Image.Image) -> str:
    import torch

    processor, model = _load()
    pixel_values = processor(images=image.convert("RGB"), return_tensors="pt").pixel_values
    with torch.no_grad():
        ids = model.generate(pixel_values, max_new_tokens=64)
    return processor.batch_decode(ids, skip_special_tokens=True)[0].strip()


def read_regions(image: Image.Image, boxes: list[tuple[int, int, int, int]]) -> list[str]:
    """Recognise each (line-level) bounding box; returns non-empty lines."""
    out: list[str] = []
    try:
        for x0, y0, x1, y1 in boxes[:MAX_REGIONS]:
            pad = 6
            crop = image.crop((max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad))
            text = read_line(crop)
            if len(text) > 2:
                out.append(text)
    except Exception as e:  # noqa: BLE001 - model download / runtime issues are non-fatal
        log.warning("Handwriting recognition failed: %s", e)
    return out
