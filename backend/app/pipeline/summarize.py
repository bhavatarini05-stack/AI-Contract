"""Plain-language summary: local LLM with a deterministic fallback."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import language as lang_mod
from app.pipeline import prompts
from app.pipeline.risk import Flag
from app.pipeline.terms import TermResult

log = logging.getLogger(__name__)


class SummaryOut(BaseModel):
    summary: str = ""
    key_points: list[str] = []


def facts(contract_type: str, entities: dict, terms: dict[str, TermResult], page_count: int) -> str:
    parties = ", ".join(
        f"{p['name']}{' (' + p['role'] + ')' if p.get('role') else ''}"
        for p in entities.get("parties", [])
    )
    lines = [f"Type: {contract_type}", f"Pages: {page_count}"]
    if parties:
        lines.append(f"Parties: {parties}")
    lines += [f"{t.label}: {t.display}" for t in terms.values()]
    return "\n".join(lines)


def summarize(
    text: str,
    contract_type: str,
    entities: dict,
    terms: dict[str, TermResult],
    flags: list[Flag],
    page_count: int,
    language: str = "en",
    llm: LLMProvider | None = None,
) -> SummaryOut:
    fact_str = facts(contract_type, entities, terms, page_count)
    if llm is not None:
        try:
            out = llm.structured(
                prompts.SUMMARY.format(
                    language=lang_mod.name(language), facts=fact_str, text=text[:12000]
                ),
                SummaryOut,
                system=prompts.SYSTEM,
            )
            if out.summary.strip():
                return out
        except LLMError as e:
            log.warning("LLM summary failed: %s", e)
    return _fallback(contract_type, entities, terms, flags, page_count)


def _fallback(contract_type, entities, terms, flags, page_count) -> SummaryOut:
    parties = [p["name"] for p in entities.get("parties", [])]
    who = " and ".join(parties[:2]) if parties else "the parties"
    t = terms
    parts = [f"This is a {page_count}-page {contract_type} between {who}."]
    if "term_length" in t and t["term_length"].value:
        parts.append(f"It lasts {t['term_length'].display}")
        if t.get("auto_renew") and t["auto_renew"].value.get("auto_renew"):
            parts[-1] += " and renews automatically unless someone gives notice"
            if "notice_period" in t and t["notice_period"].value:
                parts[-1] += f" ({t['notice_period'].display} beforehand)"
        parts[-1] += "."
    if "governing_law" in t:
        parts.append(f"It is governed by the law of {t['governing_law'].display}.")
    if "fees" in t:
        parts.append(f"Fees: {t['fees'].display}.")
    if "liability_cap" in t:
        parts.append(f"Liability cap: {t['liability_cap'].display}.")
    top = [f for f in flags if f.severity in ("critical", "high")]
    if top:
        parts.append("Main concerns: " + "; ".join(f.message.rstrip(".") for f in top[:3]) + ".")
    points = [f"{x.label}: {x.display}" for x in t.values()][:7]
    return SummaryOut(summary=" ".join(parts), key_points=points)
