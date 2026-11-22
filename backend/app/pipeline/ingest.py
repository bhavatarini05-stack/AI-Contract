"""Extract text from PDFs; route image-only (scanned) pages to OCR."""

from __future__ import annotations

import logging
from pathlib import Path

import pymupdf

from app.pipeline import handwriting, ocr
from app.pipeline.document import Document, Page

log = logging.getLogger(__name__)

MIN_TEXT_CHARS = 40  # fewer chars than this on a page → treat as scanned
LOW_OCR_CONFIDENCE = 60.0


def load_document(path: str | Path, ocr_languages: str = "eng") -> Document:
    path = Path(path)
    if path.suffix.lower() in {".txt", ".md"}:
        return _from_text(path.read_text(encoding="utf-8", errors="replace"))

    doc = Document(pages=[])
    with pymupdf.open(path) as pdf:
        for i, pg in enumerate(pdf, start=1):
            text = pg.get_text("text") or ""
            page = Page(number=i, text=text)
            if len(text.strip()) < MIN_TEXT_CHARS and _has_images(pg):
                _ocr_page(pg, page, doc, ocr_languages)
            doc.pages.append(page)

    if not any(p.text.strip() for p in doc.pages):
        doc.warnings.append("No text could be extracted from this document.")
    doc.build_text()
    return doc


def _from_text(text: str) -> Document:
    # Split plain text into pseudo-pages on form feeds, else one page.
    chunks = text.split("\f") if "\f" in text else [text]
    doc = Document(pages=[Page(number=i, text=t) for i, t in enumerate(chunks, start=1)])
    doc.build_text()
    return doc


def _has_images(pg: pymupdf.Page) -> bool:
    return bool(pg.get_images(full=False)) or bool(pg.get_drawings())


def _ocr_page(pg: pymupdf.Page, page: Page, doc: Document, langs: str) -> None:
    if not ocr.is_available():
        doc.warnings.append(
            f"Page {page.number} looks scanned but Tesseract OCR is not installed; "
            "its text was skipped. See README for setup."
        )
        return
    image = ocr.render_page(pg)
    result = ocr.ocr_image(image, langs)
    page.text, page.ocr, page.ocr_confidence = result.text, True, result.confidence
    if result.confidence < LOW_OCR_CONFIDENCE:
        doc.warnings.append(
            f"Page {page.number}: low OCR confidence ({result.confidence:.0f}%). "
            "Verify extracted terms against the original."
        )
    # Low-confidence regions on scanned pages are candidates for handwriting.
    if result.low_conf_boxes and handwriting.is_available():
        lines = handwriting.read_regions(image, result.low_conf_boxes)
        if lines:
            page.handwriting = lines
            doc.warnings.append(
                f"Page {page.number}: possible handwritten amendment detected — needs human review."
            )
