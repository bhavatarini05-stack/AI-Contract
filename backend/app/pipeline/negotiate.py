"""Negotiation suggestions derived from risk flags + playbook (+ optional local LLM)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.llm import LLMError, LLMProvider
from app.pipeline import prompts
from app.pipeline.risk import SEVERITY_WEIGHT, Flag

log = logging.getLogger(__name__)
PLAYBOOK_PATH = Path(__file__).resolve().parent.parent / "rules" / "playbook.yaml"


class NegotiateOut(BaseModel):
    suggestions: list[str] = []


@lru_cache
def playbook() -> dict:
    with open(PLAYBOOK_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["positions"]


def suggest(flags: list[Flag], contract_type: str, llm: LLMProvider | None = None) -> list[dict]:
    pb = playbook()
    ordered = sorted(flags, key=lambda f: -SEVERITY_WEIGHT.get(f.severity, 0))
    out, seen = [], set()
    for f in ordered:
        text = f.suggestion or pb.get(f.category, {}).get("ask")
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(
                {
                    "priority": f.severity,
                    "category": f.category,
                    "suggestion": text,
                    "standard_position": pb.get(f.category, {}).get("standard"),
                    "related_flag": f.rule_id,
                    "source": "playbook",
                }
            )

    if llm is not None and ordered:
        issues = "\n".join(f"- [{f.severity}] {f.message}" for f in ordered[:8])
        try:
            res = llm.structured(
                prompts.NEGOTIATE.format(contract_type=contract_type, issues=issues),
                NegotiateOut,
                system=prompts.SYSTEM,
            )
            for s in res.suggestions[:5]:
                if s.strip() and s.lower() not in seen:
                    seen.add(s.lower())
                    out.append(
                        {
                            "priority": "medium",
                            "category": "general",
                            "suggestion": s.strip(),
                            "standard_position": None,
                            "related_flag": None,
                            "source": "llm",
                        }
                    )
        except LLMError as e:
            log.warning("LLM negotiation suggestions failed: %s", e)
    return out
