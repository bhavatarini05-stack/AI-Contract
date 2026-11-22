"""Generate synthetic sample PDFs for demos and manual testing.

    python scripts/make_samples.py [output_dir]   (default: ../samples)

Creates:
  service_agreement.pdf          ~15-page text PDF (NY law, 12 months, auto-renew, 60 days notice, no cap)
  service_agreement_scanned.pdf  same contract rendered as images only (exercises OCR)
  contrato_servicios_es.pdf      Spanish contract (exercises multi-language handling)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from tests.fixtures.contracts import (  # noqa: E402
    SCHEDULE_A,
    SCHEDULE_A_HEADING,
    SERVICE_AGREEMENT,
    SPANISH_AGREEMENT,
)


def full_service_agreement() -> str:
    return (
        SERVICE_AGREEMENT
        + "\n\f"
        + SCHEDULE_A_HEADING
        + "\n\n"
        + "\n".join(SCHEDULE_A.format(n=i) for i in range(1, 72))
    )


def text_to_pdf(text: str, path: Path, fontsize: float = 10.5) -> int:
    doc = pymupdf.open()
    rect = pymupdf.paper_rect("letter")
    box = rect + (60, 60, -60, -60)
    chunks = [c for c in text.split("\f")]
    for chunk in chunks:
        remaining = chunk.strip()
        while remaining:
            page = doc.new_page(width=rect.width, height=rect.height)
            # insert as many lines as fit, carry the rest to the next page
            lines = remaining.split("\n")
            lo, hi, fit = 1, len(lines), 1
            while lo <= hi:
                mid = (lo + hi) // 2
                tmp = pymupdf.open()
                tp = tmp.new_page(width=rect.width, height=rect.height)
                if (
                    tp.insert_textbox(
                        box, "\n".join(lines[:mid]), fontsize=fontsize, fontname="helv"
                    )
                    >= 0
                ):
                    fit, lo = mid, mid + 1
                else:
                    hi = mid - 1
                tmp.close()
            page.insert_textbox(box, "\n".join(lines[:fit]), fontsize=fontsize, fontname="helv")
            remaining = "\n".join(lines[fit:]).strip()
    n = doc.page_count
    doc.save(path)
    doc.close()
    return n


def rasterize(src: Path, dst: Path, dpi: int = 200, max_pages: int = 4) -> None:
    """Make an image-only copy (no text layer), like a scanned document."""
    out = pymupdf.open()
    with pymupdf.open(src) as pdf:
        for pg in list(pdf)[:max_pages]:
            pix = pg.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
            page = out.new_page(width=pg.rect.width, height=pg.rect.height)
            page.insert_image(page.rect, pixmap=pix)
    out.save(dst)
    out.close()


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BACKEND.parent / "samples"
    out.mkdir(parents=True, exist_ok=True)
    n = text_to_pdf(full_service_agreement(), out / "service_agreement.pdf")
    rasterize(out / "service_agreement.pdf", out / "service_agreement_scanned.pdf")
    text_to_pdf(SPANISH_AGREEMENT, out / "contrato_servicios_es.pdf")
    print(f"Wrote samples to {out} (service agreement: {n} pages)")


if __name__ == "__main__":
    main()
