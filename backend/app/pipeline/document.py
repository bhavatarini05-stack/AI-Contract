"""In-memory document model shared by pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Page:
    number: int  # 1-based
    text: str
    ocr: bool = False
    ocr_confidence: float | None = None  # 0-100, Tesseract mean word confidence
    handwriting: list[str] = field(default_factory=list)  # handwritten lines recognised
    start: int = 0  # char offset of this page in Document.text
    end: int = 0


@dataclass
class Document:
    pages: list[Page]
    warnings: list[str] = field(default_factory=list)
    text: str = ""

    def build_text(self) -> None:
        """Concatenate pages and record char offsets so spans map back to pages."""
        parts, pos = [], 0
        for p in self.pages:
            body = p.text.strip()
            if p.handwriting:
                body += "\n\n[Handwritten amendment]\n" + "\n".join(p.handwriting)
            p.start, p.end = pos, pos + len(body)
            parts.append(body)
            pos = p.end + 2  # account for "\n\n" separator
        self.text = "\n\n".join(parts)

    def page_at(self, offset: int) -> int:
        for p in self.pages:
            if offset <= p.end:
                return p.number
        return self.pages[-1].number if self.pages else 1

    @property
    def page_count(self) -> int:
        return len(self.pages)
