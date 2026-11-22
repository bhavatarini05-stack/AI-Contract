"""Split contract text into top-level sections using heading heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Section:
    heading: str
    text: str
    start: int
    end: int


_HEADING_PATTERNS = [
    # "ARTICLE 5 – LIABILITY", "Section 7. Confidentiality", "Cláusula 3. Pago"
    re.compile(
        r"^[ \t]*(?:ARTICLE|Article|SECTION|Section|CLAUSE|Clause|Cláusula|CLÁUSULA|Artículo|"
        r"ARTÍCULO|Artikel|ARTIKEL|Article)\s+[\dIVXLC]+[.:\-–]?[ \t]*(?P<title>[^\n]{0,100})$",
        re.M,
    ),
    # "5. Limitation of Liability" (alone on a line) or "5. Limitation of Liability. Text..."
    re.compile(
        r"^[ \t]*(?P<num>\d{1,2})[.)][ \t]+(?P<title>[A-ZÀ-Ý][^\n.:]{2,80})(?:[.:][ \t]|[.:]?$)",
        re.M,
    ),
    # ALL-CAPS heading line: "CONFIDENTIALITY"
    re.compile(r"^[ \t]*(?P<title>[A-ZÀ-Ý][A-ZÀ-Ý &/,\-]{3,60})[ \t]*$", re.M),
]


_ATTACHMENT_RE = re.compile(
    r"^[ \t]*(?P<title>(?:SCHEDULE|Schedule|EXHIBIT|Exhibit|ANNEX|Annex|APPENDIX|Appendix|ANEXO|Anexo)"
    r"\b[^\n]{0,80}|IN WITNESS WHEREOF[^\n]{0,80})$",
    re.M,
)


def split_sections(text: str) -> list[Section]:
    best: list[re.Match] = []
    for pat in _HEADING_PATTERNS:
        matches = [m for m in pat.finditer(text) if _plausible(m)]
        if len(matches) >= 3:
            best = matches
            break
        if len(matches) > len(best):
            best = matches

    if len(best) < 2:
        return _paragraph_chunks(text)

    # Always break at schedules/exhibits/signature blocks so they don't bloat the last clause.
    extra = [
        m for m in _ATTACHMENT_RE.finditer(text) if not any(b.start() == m.start() for b in best)
    ]
    best = sorted(best + extra, key=lambda m: m.start())

    sections: list[Section] = []
    if best[0].start() > 0 and text[: best[0].start()].strip():
        sections.append(Section("Preamble", text[: best[0].start()], 0, best[0].start()))
    for i, m in enumerate(best):
        end = best[i + 1].start() if i + 1 < len(best) else len(text)
        title = (m.groupdict().get("title") or m.group(0)).strip().rstrip(".:")
        sections.append(Section(title or m.group(0).strip(), text[m.start() : end], m.start(), end))
    return sections


def _plausible(m: re.Match) -> bool:
    title = (m.groupdict().get("title") or "").strip()
    return 0 < len(title.split()) <= 10


def _paragraph_chunks(text: str, target: int = 1500) -> list[Section]:
    out, buf_start, pos = [], 0, 0
    for para in re.split(r"(\n\s*\n)", text):
        pos += len(para)
        if pos - buf_start >= target:
            out.append(Section(f"Part {len(out) + 1}", text[buf_start:pos], buf_start, pos))
            buf_start = pos
    if buf_start < len(text) and text[buf_start:].strip():
        out.append(Section(f"Part {len(out) + 1}", text[buf_start:], buf_start, len(text)))
    return out


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z(\"“])", text) if s.strip()]
