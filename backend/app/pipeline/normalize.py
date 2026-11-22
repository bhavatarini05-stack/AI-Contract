"""Normalize legal phrasing into structured values.

"twelve (12) months" → {"value": 12, "unit": "month", "days": 365}
"""

from __future__ import annotations

import re
from datetime import date

import dateparser
from dateutil.relativedelta import relativedelta

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "eighteen": 18,
    "twenty": 20,
    "twenty-four": 24,
    "thirty": 30,
    "thirty-six": 36,
    "forty-five": 45,
    "sixty": 60,
    "ninety": 90,
    "a": 1,
    "an": 1,
    "one hundred twenty": 120,
    "one hundred eighty": 180,
    # Spanish / French / German
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "seis": 6,
    "doce": 12,
    "treinta": 30,
    "sesenta": 60,
    "noventa": 90,
    "une": 1,
    "deux": 2,
    "douze": 12,
    "trente": 30,
    "soixante": 60,
    "quatre-vingt-dix": 90,
    "ein": 1,
    "eine": 1,
    "einen": 1,
    "zwei": 2,
    "drei": 3,
    "zwölf": 12,
    "dreißig": 30,
    "sechzig": 60,
    "neunzig": 90,
}
UNIT_DAYS = {"day": 1, "week": 7, "month": 30.4375, "year": 365.25}
_UNIT_ALIASES = {
    "day": "day",
    "days": "day",
    "business day": "day",
    "business days": "day",
    "calendar day": "day",
    "calendar days": "day",
    "week": "week",
    "weeks": "week",
    "month": "month",
    "months": "month",
    "year": "year",
    "years": "year",
    # multilingual
    "días": "day",
    "dias": "day",
    "día": "day",
    "jours": "day",
    "jour": "day",
    "tage": "day",
    "tagen": "day",
    "meses": "month",
    "mes": "month",
    "mois": "month",
    "monate": "month",
    "monaten": "month",
    "años": "year",
    "año": "year",
    "ans": "year",
    "an": "year",
    "jahre": "year",
    "jahren": "year",
    "jahr": "year",
}
_WORDNUM = "|".join(sorted((re.escape(w) for w in WORD_NUMBERS), key=len, reverse=True))
_UNITS = "|".join(sorted((re.escape(u) for u in _UNIT_ALIASES), key=len, reverse=True))

DURATION_RE = re.compile(
    rf"\b(?:(?:(?P<word>[^\W\d_]+(?:-[^\W\d_]+)?)\s*)?\(\s*(?P<paren>\d+)\s*\)|(?P<num>\d+)|(?P<word2>{_WORDNUM}))"
    rf"[\s-]*(?P<unit>{_UNITS})\b",
    re.I,
)

DATE_RE = re.compile(
    r"(?:"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:day of\s+)?"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}"
    r"|\d{1,2}(?:er|\.)?\s+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
    r"|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
    r"|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(?:de\s+)?\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}/\d{4}"
    r")",
    re.I,
)


def parse_duration(text: str) -> dict | None:
    m = DURATION_RE.search(text)
    if not m:
        return None
    if m.group("paren"):
        value = int(m.group("paren"))
    elif m.group("num"):
        value = int(m.group("num"))
    else:
        value = WORD_NUMBERS[(m.group("word") or m.group("word2")).lower()]
    unit = _UNIT_ALIASES[m.group("unit").lower()]
    return {
        "value": value,
        "unit": unit,
        "days": round(value * UNIT_DAYS[unit]),
        "business_days": "business" in m.group("unit").lower(),
        "text": m.group(0),
    }


def find_durations(text: str) -> list[tuple[int, int, dict]]:
    """All durations in text as (start, end, parsed)."""
    out = []
    for m in DURATION_RE.finditer(text):
        d = parse_duration(m.group(0))
        if d:
            out.append((m.start(), m.end(), d))
    return out


def notice_duration(sentence: str) -> dict | None:
    """Pick the duration that describes a notice period, not e.g. a renewal length.

    "renew for successive one (1) year periods unless ... notice ... at least sixty (60) days prior"
    → 60 days
    """
    found = find_durations(sentence)
    if not found:
        return None
    low = sentence.lower()
    best, best_score = None, -1
    for start, end, d in found:
        after, before = low[end : end + 40], low[max(0, start - 50) : start]
        score = 0
        score += (
            3 if re.search(r"\b(prior|before|in advance|notice|preaviso|préavis)\b", after) else 0
        )
        score += (
            2
            if re.search(
                r"(at least|not less than|notice of|upon|giving|with)\s*$", before.strip() + " "
            )
            else 0
        )
        score += 1 if "notice" in before or "preaviso" in before else 0
        # "notice of 30 days", "preaviso de treinta (30) días" — duration directly qualifies notice
        score += (
            4
            if re.search(r"(notice|preaviso|préavis|kündigungsfrist)\s+(?:of|de|von)?\s*$", before)
            else 0
        )
        score -= 3 if re.search(r"\b(period|term)s?\b", after[:15]) else 0
        if score > best_score:
            best, best_score = d, score
    return best


def format_duration(d: dict | None) -> str:
    if not d:
        return "—"
    unit = d["unit"] + ("s" if d["value"] != 1 else "")
    return f"{d['value']} {'business ' if d.get('business_days') else ''}{unit}"


def add_duration(start: date, d: dict) -> date:
    unit, value = d["unit"], d["value"]
    if unit == "year":
        return start + relativedelta(years=value) - relativedelta(days=1)
    if unit == "month":
        return start + relativedelta(months=value) - relativedelta(days=1)
    if unit == "week":
        return start + relativedelta(weeks=value) - relativedelta(days=1)
    return start + relativedelta(days=value - 1)


def subtract_duration(end: date, d: dict) -> date:
    unit, value = d["unit"], d["value"]
    delta = {
        "year": relativedelta(years=value),
        "month": relativedelta(months=value),
        "week": relativedelta(weeks=value),
    }.get(unit, relativedelta(days=value))
    return end - delta


def parse_date(text: str, languages: list[str] | None = None) -> date | None:
    m = DATE_RE.search(text)
    candidate = re.sub(r"(\d)(st|nd|rd|th)", r"\1", m.group(0)) if m else text
    candidate = candidate.replace("day of ", "")
    if re.search(r"\bde\s+\w+\s+de\b", candidate):
        candidate = re.sub(r"\bde\s+", "", candidate)
    dt = dateparser.parse(
        candidate,
        languages=languages,
        settings={"PREFER_DAY_OF_MONTH": "first", "STRICT_PARSING": bool(m)},
    )
    return dt.date() if dt else None


AMOUNT_RE = re.compile(
    r"(?P<cur>USD|US\$|\$|€|£|EUR|GBP|INR|Rs\.?|₹)\s?(?P<num>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s?(?P<mult>million|thousand|k|m)\b)?",
    re.I,
)
_CUR = {
    "usd": "USD",
    "us$": "USD",
    "$": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "inr": "INR",
    "rs": "INR",
    "rs.": "INR",
    "₹": "INR",
}


def parse_amount(text: str) -> dict | None:
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    value = float(m.group("num").replace(",", ""))
    mult = (m.group("mult") or "").lower()
    value *= {"million": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}.get(mult, 1)
    return {
        "value": value,
        "currency": _CUR.get(m.group("cur").lower(), m.group("cur")),
        "text": m.group(0),
    }


def parse_number_word(token: str) -> float | None:
    token = token.lower().strip()
    if re.fullmatch(r"\d+(\.\d+)?", token):
        return float(token)
    return float(WORD_NUMBERS[token]) if token in WORD_NUMBERS else None
