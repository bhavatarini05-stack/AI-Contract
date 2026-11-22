"""Runs the full analysis pipeline for a contract and persists results."""

from __future__ import annotations

import logging
import traceback
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.llm import LLMProvider, get_provider
from app.models import Clause, Contract, Job, Obligation, Report, RiskFlag, Term, utcnow
from app.pipeline import (
    classify,
    clauses,
    entities,
    ingest,
    language,
    negotiate,
    obligations,
    risk,
    sections,
    summarize,
    terms,
)
from app.pipeline.clauses import ExtractedClause
from app.pipeline.terms import TermResult

log = logging.getLogger(__name__)


def _stage(db: Session, job: Job, stage: str, progress: int) -> None:
    job.stage, job.progress = stage, progress
    db.commit()


def run_analysis(contract_id: int, job_id: int, llm: LLMProvider | None = None) -> None:
    settings = get_settings()
    llm = llm or get_provider()
    use_llm = llm if llm.health().get("ok") else None
    db = SessionLocal()
    job = db.get(Job, job_id)
    contract = db.get(Contract, contract_id)
    try:
        job.status, contract.status = "running", "processing"
        warnings: list[str] = []
        if use_llm is None:
            warnings.append(
                f"Local LLM ({llm.name}:{llm.model}) is unavailable — used rule-based analysis only. "
                "Start Ollama and pull the model for richer results."
            )
        _stage(db, job, "ingest", 5)

        doc = ingest.load_document(contract.file_path, settings.ocr_languages)
        warnings += doc.warnings
        contract.page_count = doc.page_count
        contract.full_text = doc.text
        contract.page_info = [
            {
                "page": p.number,
                "ocr": p.ocr,
                "ocr_confidence": p.ocr_confidence,
                "handwriting": p.handwriting,
                "start": p.start,
                "end": p.end,
            }
            for p in doc.pages
        ]
        _stage(db, job, "language", 20)

        lang = language.detect(doc.text)
        contract.language = lang
        if lang != "en" and use_llm is None:
            warnings.append(
                f"Document language is {language.name(lang)}; rule-based extraction is tuned for English."
            )
        _stage(db, job, "classify", 30)

        ctype, conf = classify.classify(doc.text, use_llm)
        contract.contract_type, contract.type_confidence = ctype, conf
        _stage(db, job, "entities", 40)

        ents = entities.extract(doc.text, lang, use_llm)
        contract.entities = ents
        contract.parties = ents["parties"]
        contract.governing_law = ents["governing_law"]
        _stage(db, job, "clauses", 50)

        secs = sections.split_sections(doc.text)
        extracted = clauses.extract(doc, secs, use_llm)
        grouped = clauses.by_type(extracted)
        _stage(db, job, "terms", 62)

        term_list = terms.extract_terms(doc.text, grouped, ents, lang)
        tmap = terms.as_dict(term_list)
        if "effective_date" in tmap:
            contract.effective_date = date.fromisoformat(tmap["effective_date"].value["date"])
        if "expiry_date" in tmap:
            contract.expiry_date = date.fromisoformat(tmap["expiry_date"].value["date"])
        _stage(db, job, "risk", 72)

        flags = risk.evaluate_rules(doc.text, grouped, tmap, ctype)
        if use_llm is not None:
            flags += risk.llm_review(use_llm, grouped, ctype, flags)
        score, level = risk.score(flags)
        _stage(db, job, "obligations", 82)

        obls = obligations.derive(tmap, extracted)
        _stage(db, job, "summary", 88)

        summ = summarize.summarize(
            doc.text, ctype, ents, tmap, flags, doc.page_count, lang, use_llm
        )
        suggestions = negotiate.suggest(flags, ctype, use_llm)

        _persist(
            db,
            contract,
            extracted,
            term_list,
            flags,
            obls,
            summ,
            score,
            level,
            suggestions,
            use_llm.model if use_llm else None,
        )
        contract.warnings = warnings
        contract.status = "done"
        job.status, job.stage, job.progress, job.finished_at = "done", "done", 100, utcnow()
        db.commit()
    except Exception as e:  # noqa: BLE001
        log.exception("Analysis failed for contract %s", contract_id)
        db.rollback()
        job = db.get(Job, job_id)
        contract = db.get(Contract, contract_id)
        job.status, job.error, job.finished_at = (
            "failed",
            f"{e}\n{traceback.format_exc(limit=3)}",
            utcnow(),
        )
        contract.status = "failed"
        db.commit()
    finally:
        db.close()


def _persist(
    db, contract, extracted, term_list, flags, obls, summ, score, level, suggestions, model
):
    cid = contract.id
    for model_cls in (RiskFlag, Clause, Term, Obligation, Report):
        db.execute(delete(model_cls).where(model_cls.contract_id == cid))
    db.flush()

    clause_rows: dict[str, Clause] = {}
    for c in extracted:
        row = Clause(
            contract_id=cid,
            type=c.type,
            heading=c.heading,
            text=c.text,
            page=c.page,
            start=c.start,
            end=c.end,
            confidence=c.confidence,
            source=c.source,
            needs_review=c.needs_review,
        )
        db.add(row)
        clause_rows.setdefault(c.type, row)
    db.flush()

    for t in term_list:
        db.add(
            Term(
                contract_id=cid,
                key=t.key,
                label=t.label,
                display=t.display,
                raw_text=t.raw,
                normalized_value=t.value,
                page=t.page,
            )
        )
    for f in flags:
        clause = clause_rows.get(f.clause_type or f.category)
        db.add(
            RiskFlag(
                contract_id=cid,
                clause_id=clause.id if clause else None,
                rule_id=f.rule_id,
                category=f.category,
                severity=f.severity,
                message=f.message,
                suggestion=f.suggestion,
                evidence=f.evidence,
                page=f.page or (clause.page if clause else None),
                source=f.source,
            )
        )
    for o in obls:
        db.add(
            Obligation(
                contract_id=cid,
                kind=o.kind,
                description=o.description,
                due_date=o.due_date,
                page=o.page,
            )
        )
    db.add(
        Report(
            contract_id=cid,
            summary=summ.summary,
            key_points=summ.key_points,
            risk_score=score,
            risk_level=level,
            negotiation=suggestions,
            llm_model=model,
        )
    )


# ---- helpers to rebuild pipeline objects from DB (for compare / compliance endpoints) ----


def grouped_from_db(contract: Contract) -> dict[str, list[ExtractedClause]]:
    out: dict[str, list[ExtractedClause]] = {}
    for c in contract.clauses:
        out.setdefault(c.type, []).append(
            ExtractedClause(
                c.type,
                c.heading or "",
                c.text,
                c.start or 0,
                c.end or 0,
                c.page or 1,
                c.confidence,
                c.source,
                c.needs_review,
            )
        )
    return out


def terms_from_db(contract: Contract) -> dict[str, TermResult]:
    return {
        t.key: TermResult(t.key, t.label, t.display, t.normalized_value or {}, t.raw_text, t.page)
        for t in contract.terms
    }
