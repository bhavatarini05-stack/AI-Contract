"""Integration tests against a real local Ollama server.  Run with:  pytest -m ollama"""

import pytest

from app.config import get_settings
from app.llm.ollama_provider import OllamaProvider
from app.pipeline import classify, risk, summarize
from tests.fixtures.contracts import SERVICE_AGREEMENT
from tests.test_pipeline import analyse

pytestmark = pytest.mark.ollama


@pytest.fixture(scope="module")
def llm():
    s = get_settings()
    p = OllamaProvider(s.ollama_host, s.ollama_model, s.ollama_embed_model, s.llm_timeout_seconds)
    h = p.health()
    if not h["ok"]:
        pytest.skip(f"Ollama not ready: {h.get('hint') or h.get('error')}")
    return p


def test_llm_classification(llm):
    assert classify.classify(SERVICE_AGREEMENT, llm)[0] == "Service Agreement"


def test_llm_summary(llm):
    doc, _, grouped, ents, t = analyse(SERVICE_AGREEMENT)
    flags = risk.evaluate_rules(doc.text, grouped, t)
    s = summarize.summarize(doc.text, "Service Agreement", ents, t, flags, 15, "en", llm)
    assert len(s.summary) > 50 and s.key_points


def test_llm_risk_review_returns_valid_flags(llm):
    doc, _, grouped, _, _ = analyse(SERVICE_AGREEMENT)
    flags = risk.llm_review(llm, grouped, "Service Agreement", [])
    assert all(f.severity in risk.SEVERITY_WEIGHT for f in flags)
