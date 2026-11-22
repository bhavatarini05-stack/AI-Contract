"""Compare a contract against a standard template, clause by clause."""

from __future__ import annotations

import difflib
import logging
import math
import re

from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import clauses as clause_mod
from app.pipeline import entities as ent_mod
from app.pipeline import prompts, sections, terms
from app.pipeline.document import Document, Page

log = logging.getLogger(__name__)

COMPARED_TERMS = (
    "term_length",
    "auto_renew",
    "notice_period",
    "liability_cap",
    "payment_terms",
    "governing_law",
)


class CompareOut(BaseModel):
    difference: str = ""
    less_favourable: bool = False


def analyse_text(text: str) -> tuple[dict, dict]:
    doc = Document(pages=[Page(1, text)])
    doc.build_text()
    secs = sections.split_sections(doc.text)
    cls = clause_mod.extract(doc, secs, llm=None)
    grouped = clause_mod.by_type(cls)
    ents = ent_mod.extract(doc.text)
    t = terms.as_dict(terms.extract_terms(doc.text, grouped, ents))
    return grouped, t


def compare(
    contract_grouped: dict, contract_terms: dict, template_text: str, llm: LLMProvider | None = None
) -> dict:
    tmpl_grouped, tmpl_terms = analyse_text(template_text)
    results = []
    for ctype in sorted(set(contract_grouped) | set(tmpl_grouped)):
        if ctype == "other":
            continue
        c_text = "\n".join(c.text for c in contract_grouped.get(ctype, []))
        t_text = "\n".join(c.text for c in tmpl_grouped.get(ctype, []))
        label = clause_mod.CLAUSE_LABELS.get(ctype, ctype)
        page = contract_grouped[ctype][0].page if contract_grouped.get(ctype) else None
        if not c_text:
            results.append(
                {
                    "clause_type": ctype,
                    "label": label,
                    "status": "missing",
                    "similarity": 0.0,
                    "template_text": t_text,
                    "contract_text": "",
                    "diff": [],
                    "page": None,
                    "explanation": f"The template has a {label} clause that this contract lacks.",
                }
            )
            continue
        if not t_text:
            results.append(
                {
                    "clause_type": ctype,
                    "label": label,
                    "status": "added",
                    "similarity": 0.0,
                    "template_text": "",
                    "contract_text": c_text,
                    "diff": [],
                    "page": page,
                    "explanation": f"This contract adds a {label} clause not in the template.",
                }
            )
            continue
        sim = _similarity(c_text, t_text, llm)
        status = "same" if sim >= 0.95 else "changed"
        item = {
            "clause_type": ctype,
            "label": label,
            "status": status,
            "similarity": round(sim, 3),
            "template_text": t_text,
            "contract_text": c_text,
            "diff": sentence_diff(t_text, c_text),
            "page": page,
            "explanation": None,
            "less_favourable": None,
        }
        if status == "changed" and llm is not None and ctype in clause_mod.KEY_CLAUSES:
            try:
                out = llm.structured(
                    prompts.COMPARE.format(
                        clause_type=label, template=t_text[:2500], contract=c_text[:2500]
                    ),
                    CompareOut,
                    system=prompts.SYSTEM,
                )
                if out.difference:
                    item["explanation"], item["less_favourable"] = (
                        out.difference,
                        out.less_favourable,
                    )
            except LLMError as e:
                log.warning("LLM compare failed for %s: %s", ctype, e)
        results.append(item)

    term_diffs = []
    for key in COMPARED_TERMS:
        a, b = contract_terms.get(key), tmpl_terms.get(key)
        if a is None and b is None:
            continue
        ad, bd = (a.display if a else "Not specified"), (b.display if b else "Not specified")
        term_diffs.append(
            {
                "key": key,
                "label": (a or b).label,
                "contract": ad,
                "template": bd,
                "differs": ad != bd,
            }
        )

    counts = {
        s: sum(r["status"] == s for r in results) for s in ("same", "changed", "missing", "added")
    }
    return {"clauses": results, "terms": term_diffs, "counts": counts}


def sentence_diff(a: str, b: str) -> list[dict]:
    sa, sb = sections.sentences(a), sections.sentences(b)
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=sa, b=sb, autojunk=False).get_opcodes():
        if tag == "equal":
            ops += [{"op": "equal", "text": s} for s in sa[i1:i2]]
        else:
            ops += [{"op": "delete", "text": s} for s in sa[i1:i2]]
            ops += [{"op": "insert", "text": s} for s in sb[j1:j2]]
    return ops


def _norm(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower())


def _similarity(a: str, b: str, llm: LLMProvider | None) -> float:
    lexical = difflib.SequenceMatcher(a=_norm(a), b=_norm(b), autojunk=False).ratio()
    if llm is None:
        return lexical
    try:
        ea, eb = llm.embed([a[:4000], b[:4000]])
        dot = sum(x * y for x, y in zip(ea, eb, strict=False))
        na, nb = math.sqrt(sum(x * x for x in ea)), math.sqrt(sum(y * y for y in eb))
        semantic = dot / (na * nb) if na and nb else 0.0
        return 0.5 * lexical + 0.5 * semantic
    except LLMError:
        return lexical
