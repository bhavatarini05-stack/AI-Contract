"""Check a contract against a policy (e.g. a data-privacy policy).

A policy is a list of rules:
  {id, requirement, clause_types?: [..], must_include?: [regex], must_not_include?: [regex], severity?}
Regex checks give a deterministic verdict; rules without regexes (or that are
inconclusive) are judged by the local LLM, else marked "unclear" for human review.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import prompts

log = logging.getLogger(__name__)


class VerdictOut(BaseModel):
    verdict: Literal["pass", "fail", "unclear"] = "unclear"
    explanation: str = ""
    evidence: str = ""


def check(
    policy_rules: list[dict], full_text: str, grouped: dict, llm: LLMProvider | None = None
) -> dict:
    results = []
    for rule in policy_rules:
        ctypes = rule.get("clause_types") or []
        scoped = [c for t in ctypes for c in grouped.get(t, [])]
        target = "\n".join(c.text for c in scoped) if scoped else full_text
        page = scoped[0].page if scoped else None
        verdict, explanation, evidence, source = _regex_verdict(rule, target)

        if verdict == "unclear" and llm is not None:
            try:
                out = llm.structured(
                    prompts.COMPLIANCE.format(requirement=rule["requirement"], text=target[:6000]),
                    VerdictOut,
                    system=prompts.SYSTEM,
                )
                if out.explanation:
                    verdict, explanation, evidence, source = (
                        out.verdict,
                        out.explanation,
                        out.evidence,
                        "llm",
                    )
            except LLMError as e:
                log.warning("LLM compliance check failed: %s", e)

        results.append(
            {
                "id": rule["id"],
                "requirement": rule["requirement"],
                "severity": rule.get("severity", "medium"),
                "verdict": verdict,
                "explanation": explanation,
                "evidence": evidence,
                "page": page,
                "source": source,
            }
        )

    fails = sum(r["verdict"] == "fail" for r in results)
    unclear = sum(r["verdict"] == "unclear" for r in results)
    overall = "non_compliant" if fails else "needs_review" if unclear else "compliant"
    return {
        "overall": overall,
        "passed": len(results) - fails - unclear,
        "failed": fails,
        "unclear": unclear,
        "results": results,
    }


def _regex_verdict(rule: dict, text: str) -> tuple[str, str, str, str]:
    for pat in rule.get("must_not_include", []):
        m = re.search(pat, text, re.I)
        if m:
            return "fail", "Contract contains prohibited language.", _ctx(text, m.start()), "rules"
    includes = rule.get("must_include", [])
    if not includes:
        return "unclear", "Requires judgement — no deterministic check defined.", "", "rules"
    missing = [p for p in includes if not re.search(p, text, re.I)]
    if missing:
        if len(missing) == len(includes):
            return "fail", "Required language not found in the contract.", "", "rules"
        return "unclear", "Only some of the required language was found.", "", "rules"
    m = re.search(includes[0], text, re.I)
    return "pass", "Required language found.", _ctx(text, m.start()) if m else "", "rules"


def _ctx(text: str, pos: int, width: int = 200) -> str:
    s = max(0, pos - width // 3)
    return re.sub(r"\s+", " ", text[s : s + width]).strip()
