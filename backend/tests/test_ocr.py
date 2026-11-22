import pytest

from app.pipeline import ingest, ocr


def test_scanned_pdf_without_tesseract_warns(scanned_pdf, monkeypatch):
    monkeypatch.setattr(ocr, "is_available", lambda: False)
    doc = ingest.load_document(scanned_pdf)
    assert any("Tesseract" in w for w in doc.warnings)


@pytest.mark.skipif(not ocr.is_available(), reason="Tesseract not installed")
def test_scanned_pdf_is_ocrd(scanned_pdf):
    doc = ingest.load_document(scanned_pdf)
    assert doc.pages[0].ocr
    assert doc.pages[0].ocr_confidence and doc.pages[0].ocr_confidence > 50
    assert "agreement" in doc.text.lower()
