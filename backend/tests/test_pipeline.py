"""Pipeline tests on synthetic contracts using rule-based logic (mock LLM)."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from app.llm.mock_provider import MockProvider
from app.pipeline import (
    classify,
    clauses,
    compare,
    compliance,
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
from app.pipeline.document import Document, Page
from tests.fixtures.contracts import SERVICE_AGREEMENT, SPANISH_AGREEMENT

ROOT = Path(__file__).resolve().parents[2]


def analyse(text: str):
    doc = Document(pages=[Page(1, text)])
    doc.build_text()
    secs = sections.split_sections(doc.text)
    extracted = clauses.extract(doc, secs)
    grouped = clauses.by_type(extracted)
    ents = entities.extract(doc.text)
    tmap = terms.as_dict(terms.extract_terms(doc.text, grouped, ents))
    return doc, extracted, grouped, ents, tmap


@pytest.fixture(scope="module")
def svc():
    return analyse(SERVICE_AGREEMENT)


def test_classification_and_entities(svc):
    doc, _, _, ents, _ = svc
    assert classify.classify(doc.text)[0] == "Service Agreement"
    assert ents["governing_law"] == "New York"
    assert ents["effective_date"] == "2026-01-15"
    names = {p["name"]: p["role"] for p in ents["parties"]}
    assert names == {"Brightline Analytics, Inc.": "Provider", "Harbor Retail Group LLC": "Client"}


def test_key_clauses_found(svc):
    _, _, grouped, _, _ = svc
    for key in (
        "termination",
        "liability",
        "confidentiality",
        "indemnification",
        "renewal",
        "payment",
    ):
        assert key in grouped, key


def test_key_terms(svc):
    *_, t = svc
    assert t["term_length"].display == "12 months"
    assert t["auto_renew"].value["auto_renew"] is True
    assert t["notice_period"].value["days"] == 60
    assert t["liability_cap"].value["present"] is False
    assert t["payment_terms"].value["days"] == 30
    assert t["expiry_date"].value["date"] == "2027-01-14"


def test_risk_flags(svc):
    doc, _, grouped, _, t = svc
    flags = risk.evaluate_rules(doc.text, grouped, t, "Service Agreement")
    ids = {f.rule_id for f in flags}
    assert "liability_cap_missing" in ids
    assert "indemnification_broad" in ids
    assert "unilateral_termination" in ids
    assert "missing_dispute_resolution" not in ids  # courts of New York County are named
    msg = next(f.message for f in flags if f.rule_id == "liability_cap_missing")
    assert msg == "Liability cap is missing — standard is 1x fees"
    score, level = risk.score(flags)
    assert 50 <= score <= 100 and level in {"high", "critical"}


def test_unlimited_liability_flag():
    text = SERVICE_AGREEMENT.replace(
        "In no event shall Provider be liable for any indirect",
        "Client shall have unlimited liability under this Agreement. In no event shall Provider be liable for any indirect",
    )
    doc, _, grouped, _, t = analyse(text)
    ids = {f.rule_id for f in risk.evaluate_rules(doc.text, grouped, t)}
    assert "unlimited_liability" in ids and "liability_cap_missing" not in ids


def test_cap_detected_when_present():
    text = SERVICE_AGREEMENT.replace(
        "In no event shall Provider be liable",
        "Each party's aggregate liability shall not exceed the fees paid in the twelve (12) months preceding the claim. In no event shall Provider be liable",
    )
    *_, t = analyse(text)
    assert t["liability_cap"].value["present"] is True
    assert t["liability_cap"].value["multiple_of_fees"] == 1.0


def test_obligations_renewal_deadline(svc):
    _, extracted, _, _, t = svc
    obls = obligations.derive(t, extracted)
    notice = next(o for o in obls if o.kind == "renewal_notice")
    assert notice.due_date == date(2026, 11, 15)
    assert "must be sent by November 15, 2026" in notice.description
    expiry = next(o for o in obls if o.kind == "expiry")
    assert expiry.due_date == date(2027, 1, 14)


@pytest.mark.parametrize(
    "due,today,already,expected",
    [
        (date(2026, 6, 1), date(2026, 5, 2), set(), 30),
        (date(2026, 6, 1), date(2026, 5, 2), {30}, None),
        (date(2026, 6, 1), date(2026, 1, 1), set(), None),
        (date(2026, 6, 1), date(2026, 6, 2), set(), -1),
        (date(2026, 6, 1), date(2026, 5, 30), {90, 60, 30}, 7),
    ],
)
def test_alert_thresholds(due, today, already, expected):
    assert obligations.alert_for(due, today, already) == expected


def test_alert_message():
    msg = obligations.alert_message("expiry", "", date(2026, 6, 1), date(2026, 5, 2))
    assert msg.startswith("This contract expires in 30 days")


def test_summary_fallback_and_negotiation(svc):
    doc, _, grouped, ents, t = svc
    flags = risk.evaluate_rules(doc.text, grouped, t)
    s = summarize.summarize(
        doc.text, "Service Agreement", ents, t, flags, 1, "en", llm=MockProvider()
    )
    assert "Brightline Analytics" in s.summary and "12 months" in s.summary
    sugg = negotiate.suggest(flags, "Service Agreement", llm=MockProvider())
    assert any("cap on liability" in x["suggestion"].lower() for x in sugg)
    assert sugg[0]["priority"] in {"critical", "high"}


def test_llm_flags_are_merged():
    llm = MockProvider(
        {
            "indemnification clause": {
                "issues": [
                    {
                        "severity": "high",
                        "message": "Indemnity covers Provider's own negligence.",
                        "suggestion": "Exclude it.",
                    }
                ]
            }
        }
    )
    doc, _, grouped, _, t = analyse(SERVICE_AGREEMENT)
    flags = risk.llm_review(llm, grouped, "Service Agreement", [])
    assert any(f.source == "llm" and "own negligence" in f.message for f in flags)


def test_compare_with_template(svc):
    _, _, grouped, _, t = svc
    tmpl = (ROOT / "templates" / "standard_service_agreement.md").read_text(encoding="utf-8")
    res = compare.compare(grouped, t, tmpl)
    by_key = {x["key"]: x for x in res["terms"]}
    assert by_key["notice_period"]["differs"] and by_key["notice_period"]["template"] == "30 days"
    assert by_key["liability_cap"]["differs"]
    assert not by_key["term_length"]["differs"]
    liab = next(c for c in res["clauses"] if c["clause_type"] == "liability")
    assert liab["status"] == "changed" and any(op["op"] == "insert" for op in liab["diff"])


def test_compliance_privacy_policy(svc):
    doc, _, grouped, _, _ = svc
    policy = yaml.safe_load(
        (ROOT / "backend/app/rules/sample_privacy_policy.yaml").read_text(encoding="utf-8")
    )
    res = compliance.check(policy["rules"], doc.text, grouped)
    verdicts = {r["id"]: r["verdict"] for r in res["results"]}
    assert verdicts["dp_breach_notification"] == "fail"
    assert res["overall"] == "non_compliant"


def test_spanish_contract():
    doc, _, grouped, ents, t = analyse(SPANISH_AGREEMENT)
    assert language.detect(doc.text) == "es"
    assert ents["effective_date"] == "2026-03-01"
    assert t["term_length"].value["value"] == 12
    assert t["notice_period"].value["days"] == 30
    assert t["liability_cap"].value["present"] is True


def test_ingest_text_pdf(service_pdf):
    doc = ingest.load_document(service_pdf)
    assert doc.page_count == 15
    assert "Limitation of Liability" in doc.text
    assert not any(p.ocr for p in doc.pages)


def test_ingest_blank_pdf_warns(blank_pdf):
    doc = ingest.load_document(blank_pdf)
    assert doc.warnings
