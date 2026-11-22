"""Language detection (lingua if installed, else a stop-word heuristic)."""

from __future__ import annotations

import re
from functools import lru_cache

# ISO 639-1 → Tesseract language pack code
TESSERACT_CODES = {
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "de": "deu",
    "it": "ita",
    "pt": "por",
    "nl": "nld",
    "hi": "hin",
    "zh": "chi_sim",
    "ja": "jpn",
}
NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "hi": "Hindi",
    "zh": "Chinese",
    "ja": "Japanese",
}

_STOPWORDS = {
    "en": {"the", "and", "of", "to", "shall", "this", "agreement", "party", "in", "or"},
    "es": {"el", "la", "de", "y", "que", "en", "los", "las", "contrato", "parte"},
    "fr": {"le", "la", "de", "et", "les", "des", "contrat", "partie", "est", "du"},
    "de": {"der", "die", "und", "das", "den", "vertrag", "partei", "ist", "von", "zu"},
    "it": {"il", "la", "di", "e", "che", "contratto", "parte", "del", "della", "per"},
    "pt": {"o", "a", "de", "e", "que", "contrato", "parte", "do", "da", "em"},
    "nl": {"de", "het", "en", "van", "een", "overeenkomst", "partij", "is", "dat", "op"},
}


@lru_cache
def _lingua():
    try:
        from lingua import LanguageDetectorBuilder

        return LanguageDetectorBuilder.from_all_languages().with_low_accuracy_mode().build()
    except ImportError:
        return None


def detect(text: str) -> str:
    sample = text[:5000]
    if not sample.strip():
        return "en"
    det = _lingua()
    if det is not None:
        lang = det.detect_language_of(sample)
        if lang is not None:
            return lang.iso_code_639_1.name.lower()
    words = re.findall(r"[a-zà-ÿ]+", sample.lower())
    scores = {lang: sum(w in sw for w in words) for lang, sw in _STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "en"


def name(code: str) -> str:
    return NAMES.get(code, code)
