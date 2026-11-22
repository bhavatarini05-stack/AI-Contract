"""Legal entity recognition: parties, governing law, dates, amounts, emails.

Regex first (fast, deterministic); spaCy adds ORG/GPE if installed; the local LLM
fills gaps the rules could not resolve.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import normalize, prompts

log = logging.getLogger(__name__)

_SUFFIX = (
    r"(?:Inc\.?|Incorporated|LLC|L\.L\.C\.|Ltd\.?|Limited|LLP|Corp\.?|Corporation|Company|Co\.|"
    r"GmbH|AG|S\.A\.|S\.L\.|SAS|S\.A\.S\.|B\.V\.|N\.V\.|PLC|plc|Pvt\.? Ltd\.?|Private Limited)(?![A-Za-z])"
)
PARTY_RE = re.compile(
    rf"(?P<name>[A-Z][\w&'.\-]*(?:\s+(?:[A-ZÀ-Ý&][\w&'.\-]*|de|del|la|of|and|y|und|für|du|des)){{0,6}},?\s+{_SUFFIX})"
    r"(?:[^()]{0,120}?\(\s*(?:hereinafter\s+)?[\"“']?(?:the\s+|el\s+|la\s+|le\s+|der\s+|die\s+)?[\"“']?(?P<role>[A-ZÀ-Ý][\wÀ-ÿ ]{1,30}?)[\"”']?\s*\))?"
)
GOV_LAW_RE = re.compile(
    r"(?:governed by|construed (?:and enforced )?in accordance with|subject to)"
    r"(?: and construed in accordance with)?\s+the\s+laws?\s+of\s+(?:the\s+)?"
    r"(?:State of |Commonwealth of |Province of |Republic of )?"
    r"(?P<law>[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})",
)
GOV_LAW_INTL_RE = re.compile(
    r"(?:leyes de|lois de|droit|Recht der|recht von)\s+(?:la |le |l'|der )?(?P<law>[A-ZÀ-Ý][\wÀ-ÿ]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ]+){0,2})"
)
EFFECTIVE_RE = re.compile(
    r"(?:effective\s+(?:as\s+of|date[^\n]{0,15}?)|dated(?:\s+as\s+of)?|entered\s+into\s+(?:as\s+of|on)"
    r"|made\s+(?:as\s+of|on))[\s:,]*(?P<date>" + normalize.DATE_RE.pattern + ")",
    re.I,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class _Party(BaseModel):
    name: str = ""
    role: str = ""


class EntitiesOut(BaseModel):
    parties: list[_Party] = []
    governing_law: str = ""
    effective_date: str = ""


def extract(text: str, language: str = "en", llm: LLMProvider | None = None) -> dict:
    head = re.sub(r"\s+", " ", text[:6000])
    parties = _parties(head)
    gov = _governing_law(text)
    eff_match = EFFECTIVE_RE.search(text[:8000])
    effective = normalize.parse_date(eff_match.group("date")) if eff_match else None
    if effective is None:
        first = normalize.DATE_RE.search(head)
        effective = normalize.parse_date(first.group(0)) if first else None

    amounts = []
    for m in normalize.AMOUNT_RE.finditer(text):
        a = normalize.parse_amount(m.group(0))
        if a and a not in amounts:
            amounts.append(a)

    ent = {
        "parties": parties,
        "governing_law": gov,
        "effective_date": effective.isoformat() if effective else None,
        "amounts": amounts[:20],
        "emails": sorted(set(EMAIL_RE.findall(text)))[:10],
        "organizations": [],
        "locations": [],
    }
    _spacy_enrich(head, language, ent)

    if llm is not None and (not parties or not gov or not effective):
        try:
            out = llm.structured(
                prompts.ENTITIES.format(text=head[:3500]), EntitiesOut, system=prompts.SYSTEM
            )
            if not ent["parties"] and out.parties:
                ent["parties"] = [p.model_dump() for p in out.parties if p.name][:6]
            if not ent["governing_law"] and out.governing_law:
                ent["governing_law"] = out.governing_law.strip()
            if not ent["effective_date"] and out.effective_date:
                d = normalize.parse_date(out.effective_date)
                ent["effective_date"] = d.isoformat() if d else None
        except LLMError as e:
            log.warning("LLM entity extraction failed: %s", e)
    return ent


def _parties(text: str) -> list[dict]:
    seen, out = set(), []
    for m in PARTY_RE.finditer(text):
        name = re.sub(r"\s+", " ", m.group("name")).strip(" ,")
        # "Effective Date. Brightline Analytics, Inc." → keep the part after the sentence break
        name = re.split(r"[.;:]\s+(?=[A-Z])", name)[-1]
        name = re.sub(r"^(?:This|The|By|Between|And|BETWEEN|AND)\s+", "", name)
        if not re.search(r"[a-z]", name.split()[0]):  # e.g. ALL-CAPS title words
            continue
        key = name.lower()
        if key in seen or len(name) > 90:
            continue
        seen.add(key)
        out.append({"name": name, "role": (m.group("role") or "").strip()})
        if len(out) >= 6:
            break
    return out


def _governing_law(text: str) -> str | None:
    m = GOV_LAW_RE.search(text) or GOV_LAW_INTL_RE.search(text)
    if not m:
        return None
    law = re.sub(r"\s+", " ", m.group("law"))
    law = re.sub(r"\s+(?:without|and|excluding|applicable|which)\b.*$", "", law).strip()
    return law


@lru_cache
def _nlp(language: str):
    try:
        import spacy
    except ImportError:
        return None
    for model in (("en_core_web_sm",) if language == "en" else ()) + ("xx_ent_wiki_sm",):
        try:
            return spacy.load(model)
        except OSError:
            continue
    return None


def _spacy_enrich(text: str, language: str, ent: dict) -> None:
    nlp = _nlp(language)
    if nlp is None:
        return
    doc = nlp(text[:5000])
    orgs = {e.text.strip() for e in doc.ents if e.label_ in {"ORG"}}
    locs = {e.text.strip() for e in doc.ents if e.label_ in {"GPE", "LOC"}}
    ent["organizations"] = sorted(orgs)[:15]
    ent["locations"] = sorted(locs)[:15]
