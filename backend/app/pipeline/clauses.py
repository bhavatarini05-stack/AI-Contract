"""Identify key clauses (termination, liability, confidentiality, ...) in sections."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import prompts
from app.pipeline.document import Document
from app.pipeline.sections import Section

log = logging.getLogger(__name__)

# keyword patterns (English + common Spanish/French/German terms)
CLAUSE_PATTERNS: dict[str, list[str]] = {
    "term": [
        r"^term\b",
        r"\bterm of (?:this|the) agreement",
        r"initial term",
        r"\bduración\b",
        r"\bdurée\b",
        r"\blaufzeit\b",
    ],
    "renewal": [r"renew", r"renovaci", r"renouvel", r"verlängerung"],
    "termination": [r"terminat", r"rescisi", r"résiliation", r"kündigung"],
    "liability": [
        r"limitation of liability",
        r"\bliabilit",
        r"consequential damages",
        r"responsabilidad",
        r"responsabilité",
        r"haftung",
    ],
    "indemnification": [r"indemn", r"hold harmless", r"freistellung"],
    "confidentiality": [
        r"confidential",
        r"non-disclosure",
        r"confidencial",
        r"confidentialité",
        r"vertraulich",
    ],
    "payment": [
        r"payment",
        r"\bfees?\b",
        r"invoic",
        r"compensation",
        r"\bpago\b",
        r"paiement",
        r"zahlung",
        r"vergütung",
    ],
    "intellectual_property": [
        r"intellectual property",
        r"\bownership\b",
        r"license grant",
        r"propiedad intelectual",
        r"propriété intellectuelle",
        r"geistiges eigentum",
    ],
    "governing_law": [
        r"governing law",
        r"\bjurisdiction\b",
        r"choice of law",
        r"ley aplicable",
        r"droit applicable",
        r"anwendbares recht",
    ],
    "dispute_resolution": [r"dispute", r"arbitrat", r"mediat"],
    "data_protection": [
        r"data protection",
        r"privacy",
        r"personal data",
        r"\bgdpr\b",
        r"protección de datos",
        r"données personnelles",
        r"datenschutz",
    ],
    "warranty": [r"warrant", r"garantía", r"garantie", r"gewährleistung"],
    "force_majeure": [r"force majeure", r"fuerza mayor", r"höhere gewalt"],
    "assignment": [r"\bassignment\b", r"\bassign\b", r"cesión", r"cession", r"abtretung"],
    "non_compete": [r"non-?compet", r"non-?solicit", r"no competencia", r"wettbewerbsverbot"],
    "insurance": [r"\binsurance\b", r"\bseguro\b", r"\bassurance\b", r"versicherung"],
    "audit": [r"\baudit\b", r"inspection rights"],
}
CLAUSE_LABELS = {
    "term": "Term",
    "renewal": "Renewal",
    "termination": "Termination",
    "liability": "Limitation of Liability",
    "indemnification": "Indemnification",
    "confidentiality": "Confidentiality",
    "payment": "Payment & Fees",
    "intellectual_property": "Intellectual Property",
    "governing_law": "Governing Law",
    "dispute_resolution": "Dispute Resolution",
    "data_protection": "Data Protection & Privacy",
    "warranty": "Warranties",
    "force_majeure": "Force Majeure",
    "assignment": "Assignment",
    "non_compete": "Non-Compete / Non-Solicit",
    "insurance": "Insurance",
    "audit": "Audit",
    "other": "Other",
}
KEY_CLAUSES = (
    "termination",
    "liability",
    "confidentiality",
    "indemnification",
    "renewal",
    "payment",
    "intellectual_property",
)


@dataclass
class ExtractedClause:
    type: str
    heading: str
    text: str
    start: int
    end: int
    page: int
    confidence: float
    source: str = "rules"
    needs_review: bool = False


class ClauseTypeOut(BaseModel):
    clause_type: Literal[tuple(list(CLAUSE_PATTERNS) + ["other"])] = "other"  # type: ignore[valid-type]


def _score(patterns: list[str], text: str) -> int:
    return sum(len(re.findall(p, text, re.I | re.M)) for p in patterns)


def extract(
    doc: Document, sections: list[Section], llm: LLMProvider | None = None
) -> list[ExtractedClause]:
    out: list[ExtractedClause] = []
    for sec in sections:
        heading = sec.heading.lower()
        body = sec.text.lower()
        types: list[tuple[str, float, str]] = []
        for ctype, pats in CLAUSE_PATTERNS.items():
            if any(re.search(p, heading, re.I) for p in pats):
                types.append((ctype, 0.9, "rules"))
        if not types:
            # fall back to body keywords; require a clear winner
            scores = {c: _score(p, body) for c, p in CLAUSE_PATTERNS.items()}
            best = max(scores, key=scores.get)
            if scores[best] >= 3:
                types.append((best, 0.6, "rules"))
            elif llm is not None and sec.heading != "Preamble" and len(sec.text.strip()) > 80:
                t = _llm_type(llm, sec)
                if t:
                    types.append((t, 0.7, "llm"))
        handwritten = "[handwritten amendment]" in body
        for ctype, conf, source in types:
            out.append(
                ExtractedClause(
                    type=ctype,
                    heading=sec.heading,
                    text=sec.text.strip(),
                    start=sec.start,
                    end=sec.end,
                    page=doc.page_at(sec.start),
                    confidence=conf,
                    source=source,
                    needs_review=handwritten
                    or any(
                        p.number == doc.page_at(sec.start)
                        and (p.handwriting or (p.ocr_confidence or 100) < 60)
                        for p in doc.pages
                    ),
                )
            )
    return out


def _llm_type(llm: LLMProvider, sec: Section) -> str | None:
    try:
        out = llm.structured(
            prompts.CLAUSE_TYPE.format(
                types=", ".join(list(CLAUSE_PATTERNS) + ["other"]),
                heading=sec.heading,
                text=sec.text[:2000],
            ),
            ClauseTypeOut,
            system=prompts.SYSTEM,
        )
        return None if out.clause_type == "other" else out.clause_type
    except LLMError as e:
        log.warning("LLM clause typing failed: %s", e)
        return None


def by_type(clauses: list[ExtractedClause]) -> dict[str, list[ExtractedClause]]:
    grouped: dict[str, list[ExtractedClause]] = {}
    for c in clauses:
        grouped.setdefault(c.type, []).append(c)
    return grouped
