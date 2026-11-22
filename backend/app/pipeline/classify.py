"""Contract-type classification: keyword scoring + optional LLM confirmation."""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import prompts

log = logging.getLogger(__name__)

CONTRACT_TYPES: dict[str, list[str]] = {
    "Service Agreement": [
        r"services? agreement",
        r"statement of work",
        r"\bservices\b",
        r"service provider",
    ],
    "Master Services Agreement": [r"master services? agreement", r"\bmsa\b"],
    "Non-Disclosure Agreement": [
        r"non-?disclosure",
        r"confidentiality agreement",
        r"\bnda\b",
        r"acuerdo de confidencialidad",
    ],
    "Employment Agreement": [
        r"employment agreement",
        r"\bemployee\b",
        r"\bemployer\b",
        r"\bsalary\b",
    ],
    "Consulting Agreement": [r"consult(ing|ant) agreement", r"\bconsultant\b"],
    "SaaS / Subscription Agreement": [
        r"software as a service",
        r"\bsaas\b",
        r"subscription",
        r"\bsubscriber\b",
    ],
    "Software License Agreement": [
        r"license agreement",
        r"\blicensee\b",
        r"\blicensor\b",
        r"end user license",
    ],
    "Lease Agreement": [
        r"lease agreement",
        r"\blandlord\b",
        r"\btenant\b",
        r"\bpremises\b",
        r"contrato de arrendamiento",
    ],
    "Purchase / Supply Agreement": [
        r"purchase agreement",
        r"supply agreement",
        r"\bsupplier\b",
        r"\bpurchase orders?\b",
    ],
    "Partnership Agreement": [r"partnership agreement", r"joint venture"],
    "Loan Agreement": [r"loan agreement", r"\bborrower\b", r"\blender\b", r"\bprincipal amount\b"],
    "Data Processing Agreement": [
        r"data processing agreement",
        r"\bdpa\b",
        r"\bprocessor\b",
        r"\bcontroller\b",
    ],
}


class ClassifyOut(BaseModel):
    contract_type: Literal[tuple(list(CONTRACT_TYPES) + ["Other"])] | None = None  # type: ignore[valid-type]


def classify(text: str, llm: LLMProvider | None = None) -> tuple[str, float]:
    head = text[:4000].lower()
    title = text[:300].lower()
    scores: dict[str, float] = {}
    for ctype, pats in CONTRACT_TYPES.items():
        s = 0.0
        for i, p in enumerate(pats):
            hits = len(re.findall(p, head))
            if hits:
                weight = 3.0 if i == 0 else 1.0
                s += weight * min(hits, 5)
                if re.search(p, title):
                    s += 5.0
        scores[ctype] = s
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1.0
    rule_type, rule_conf = (
        (best, round(scores[best] / total, 2)) if scores[best] else ("Other", 0.0)
    )

    if llm is not None:
        try:
            out = llm.structured(
                prompts.CLASSIFY.format(
                    types="\n".join(f"- {t}" for t in CONTRACT_TYPES), text=text[:3000]
                ),
                ClassifyOut,
                system=prompts.SYSTEM,
            )
            if out.contract_type and out.contract_type != "Other":
                agree = out.contract_type == rule_type
                return out.contract_type, 0.95 if agree else 0.75
        except LLMError as e:
            log.warning("LLM classification failed: %s", e)
    return rule_type, rule_conf
