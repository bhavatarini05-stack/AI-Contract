"""Risk analysis: deterministic YAML rules + optional local-LLM clause review → 0-100 score."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import prompts
from app.pipeline.clauses import CLAUSE_LABELS, ExtractedClause
from app.pipeline.terms import TermResult

log = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "risk_rules.yaml"
SEVERITY_WEIGHT = {"critical": 30, "high": 20, "medium": 10, "low": 4}
LLM_REVIEW_CLAUSES = (
    "indemnification",
    "liability",
    "termination",
    "intellectual_property",
    "confidentiality",
    "renewal",
    "data_protection",
    "non_compete",
    "payment",
)


@dataclass
class Flag:
    rule_id: str
    category: str
    severity: str
    message: str
    suggestion: str | None = None
    evidence: str | None = None
    page: int | None = None
    clause_type: str | None = None
    source: str = "rules"


class _Issue(BaseModel):
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    message: str = ""
    suggestion: str = ""


class ReviewOut(BaseModel):
    issues: list[_Issue] = []


@lru_cache
def load_rules(path: str | None = None) -> list[dict]:
    with open(path or RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["rules"]


def evaluate_rules(
    text: str,
    grouped: dict[str, list[ExtractedClause]],
    terms: dict[str, TermResult],
    contract_type: str | None = None,
    rules: list[dict] | None = None,
) -> list[Flag]:
    flags: list[Flag] = []
    for rule in rules if rules is not None else load_rules():
        if rule.get("applies_to") and contract_type and contract_type not in rule["applies_to"]:
            continue
        hit = _check(rule["when"], text, grouped, terms)
        if hit is None:
            continue
        evidence, page, ctype = hit
        flags.append(
            Flag(
                rule["id"],
                rule["category"],
                rule["severity"],
                rule["message"],
                rule.get("suggestion"),
                evidence,
                page,
                ctype,
            )
        )
    return flags


def _check(
    when: dict, text: str, grouped, terms
) -> tuple[str | None, int | None, str | None] | None:
    """Return (evidence, page, clause_type) when the rule fires, else None."""
    kind, cfg = next(iter(when.items()))
    if kind == "missing_clause":
        return (None, None, cfg["clause"]) if not grouped.get(cfg["clause"]) else None

    if kind == "term":
        t = terms.get(cfg["key"])
        op = str(cfg["op"])
        if op == "missing":
            return (None, None, None) if t is None else None
        if t is None:
            return None
        v = t.value.get(cfg["field"]) if cfg.get("field") else t.value
        num = isinstance(v, (int, float)) and not isinstance(v, bool)
        if op == "true":
            ok = v is True
        elif op == "false":
            ok = v is False
        elif op == "eq":
            ok = v == cfg.get("value")
        elif op == "ne":
            ok = v != cfg.get("value")
        elif op == "gt":
            ok = num and v > cfg["value"]
        elif op == "lt":
            ok = num and v < cfg["value"]
        else:
            raise ValueError(f"Unknown term op: {op}")
        return (t.raw, t.page, None) if ok else None

    if kind == "pattern":
        targets = grouped.get(cfg["clause"], []) if cfg.get("clause") else [None]
        for c in targets:
            body = c.text if c else text
            m = re.search(cfg["regex"], body, re.I)
            if m and not (cfg.get("unless") and re.search(cfg["unless"], body, re.I)):
                return (_context(body, m.start()), c.page if c else None, cfg.get("clause"))
        return None

    if kind == "absent_pattern":
        cls = grouped.get(cfg["clause"], [])
        if cls and not any(re.search(cfg["regex"], c.text, re.I) for c in cls):
            return (cls[0].text[:300], cls[0].page, cfg["clause"])
        return None

    if kind == "text_without_clause":
        m = re.search(cfg["regex"], text, re.I)
        if m and not grouped.get(cfg["clause"]):
            return (_context(text, m.start()), None, cfg["clause"])
        return None

    if kind == "text_absent":
        return None if re.search(cfg["regex"], text, re.I) else (None, None, None)

    raise ValueError(f"Unknown rule condition: {kind}")


def _context(body: str, pos: int, width: int = 160) -> str:
    s = max(0, pos - width // 2)
    return re.sub(r"\s+", " ", body[s : pos + width]).strip()


def llm_review(
    llm: LLMProvider,
    grouped: dict[str, list[ExtractedClause]],
    contract_type: str,
    existing: list[Flag],
) -> list[Flag]:
    flagged = {f.message.lower() for f in existing}
    out: list[Flag] = []
    for ctype in LLM_REVIEW_CLAUSES:
        for c in grouped.get(ctype, [])[:1]:
            try:
                res = llm.structured(
                    prompts.RISK_REVIEW.format(
                        clause_type=CLAUSE_LABELS.get(ctype, ctype),
                        contract_type=contract_type or "contract",
                        text=c.text[:3000],
                    ),
                    ReviewOut,
                    system=prompts.SYSTEM,
                )
            except LLMError as e:
                log.warning("LLM risk review failed for %s: %s", ctype, e)
                continue
            for issue in res.issues[:2]:
                if issue.message and issue.message.lower() not in flagged:
                    out.append(
                        Flag(
                            f"llm_{ctype}",
                            ctype,
                            issue.severity,
                            issue.message.strip(),
                            issue.suggestion.strip() or None,
                            c.text[:300],
                            c.page,
                            ctype,
                            "llm",
                        )
                    )
    return out


LLM_FLAG_WEIGHT = 0.5  # AI-found issues are less certain than deterministic rule hits


def score(flags: list[Flag]) -> tuple[int, str]:
    raw = sum(
        SEVERITY_WEIGHT.get(f.severity, 0) * (LLM_FLAG_WEIGHT if f.source == "llm" else 1.0)
        for f in flags
    )
    total = min(100, round(raw))
    level = (
        "low" if total < 25 else "medium" if total < 50 else "high" if total < 75 else "critical"
    )
    return total, level
