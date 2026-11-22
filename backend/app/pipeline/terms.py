"""Extract and normalize key commercial terms from classified clauses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.pipeline import normalize
from app.pipeline.clauses import ExtractedClause
from app.pipeline.sections import sentences


@dataclass
class TermResult:
    key: str
    label: str
    display: str
    value: dict = field(default_factory=dict)
    raw: str | None = None
    page: int | None = None


def _sentences_of(clauses: list[ExtractedClause]) -> list[tuple[str, ExtractedClause]]:
    return [(s, c) for c in clauses for s in sentences(c.text)]


def extract_terms(
    text: str, grouped: dict[str, list[ExtractedClause]], entities: dict, language: str = "en"
) -> list[TermResult]:
    terms: list[TermResult] = []
    term_cls = grouped.get("term", []) + grouped.get("renewal", []) + grouped.get("termination", [])
    # If nothing was classified, search the whole text.
    pool = _sentences_of(term_cls) or [(s, None) for s in sentences(text)]

    # --- Term length -----------------------------------------------------------------------
    term_len, term_raw, term_page = None, None, None
    for s, c in pool:
        low = s.lower()
        if re.search(
            r"\b(initial term|term of (?:this|the) agreement|period of|shall (?:remain|continue) in (?:full )?(?:force|effect)|commence|duración|durée|laufzeit)\b",
            low,
        ) and not re.search(r"notice|renewal term|successive|prior to", low):
            d = normalize.parse_duration(s)
            if d and d["days"] >= 28:
                term_len, term_raw, term_page = d, s, c.page if c else None
                break
    terms.append(
        TermResult(
            "term_length",
            "Term",
            normalize.format_duration(term_len) if term_len else "Not specified",
            term_len or {},
            term_raw,
            term_page,
        )
    )

    # --- Auto-renewal ------------------------------------------------------------------------
    renew_sent, renew_c = None, None
    for s, c in pool:
        if re.search(
            r"automatic(?:ally)? renew|auto-?renew|shall (?:be )?renew|successive|evergreen|se renovará automáticamente|reconduction tacite|verlängert sich automatisch",
            s,
            re.I,
        ):
            renew_sent, renew_c = s, c
            break
    mutual_only = any(
        re.search(r"renew\w* (?:only )?(?:upon|by) mutual|may be renewed by mutual", s, re.I)
        for s, _ in pool
    )
    auto = bool(renew_sent) and not mutual_only
    renewal_period = _renewal_period(renew_sent) if renew_sent else None
    disp = (
        "Yes"
        + (
            f" ({normalize.format_duration(renewal_period)} periods)"
            if auto and renewal_period
            else ""
        )
        if auto
        else "No"
    )
    terms.append(
        TermResult(
            "auto_renew",
            "Auto-renew",
            disp,
            {"auto_renew": auto, "renewal_period": renewal_period},
            renew_sent,
            renew_c.page if renew_c else None,
        )
    )

    # --- Notice period (non-renewal / termination) ------------------------------------------
    notice, notice_raw, notice_page, notice_ctx = None, None, None, None
    candidates = []
    for s, c in pool:
        low = s.lower()
        if "notice" in low or "preaviso" in low or "préavis" in low or "kündigungsfrist" in low:
            d = normalize.notice_duration(s)
            if d:
                ctx = "renewal" if re.search(r"renew|non-renewal", low) else "termination"
                candidates.append((0 if ctx == "renewal" else 1, d, s, c, ctx))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        _, notice, notice_raw, nc, notice_ctx = candidates[0]
        notice_page = nc.page if nc else None
    terms.append(
        TermResult(
            "notice_period",
            "Notice",
            normalize.format_duration(notice) if notice else "Not specified",
            {**(notice or {}), "context": notice_ctx} if notice else {},
            notice_raw,
            notice_page,
        )
    )

    # --- Liability cap ----------------------------------------------------------------------
    terms.append(_liability_cap(grouped.get("liability", [])))

    # --- Payment terms ----------------------------------------------------------------------
    pay = None
    for s, c in _sentences_of(grouped.get("payment", [])):
        m = re.search(
            r"(?:net|within)\s+((?:\w+\s*\(\d+\))|\d+|\w+)\s*(?:calendar\s+|business\s+)?days",
            s,
            re.I,
        )
        if m:
            d = normalize.parse_duration(
                m.group(0).replace("net ", "").replace("Net ", "")
            ) or normalize.parse_duration(s)
            if d:
                pay = TermResult(
                    "payment_terms", "Payment terms", f"Net {d['days']} days", d, s, c.page
                )
                break
    if pay:
        terms.append(pay)

    # fees
    fee = None
    for s, c in _sentences_of(grouped.get("payment", [])):
        a = normalize.parse_amount(s)
        if a:
            per = re.search(
                r"per (month|year|annum|hour|quarter)|(monthly|annual(?:ly)?|quarterly|hourly)",
                s,
                re.I,
            )
            label = f"{a['currency']} {a['value']:,.2f}" + (f" ({per.group(0)})" if per else "")
            fee = TermResult(
                "fees", "Fees", label, {**a, "period": per.group(0) if per else None}, s, c.page
            )
            break
    if fee:
        terms.append(fee)

    # --- Governing law & dates --------------------------------------------------------------
    if entities.get("governing_law"):
        terms.append(
            TermResult(
                "governing_law",
                "Governing law",
                entities["governing_law"],
                {"jurisdiction": entities["governing_law"]},
            )
        )
    eff = date.fromisoformat(entities["effective_date"]) if entities.get("effective_date") else None
    if eff:
        terms.append(
            TermResult(
                "effective_date", "Effective date", eff.isoformat(), {"date": eff.isoformat()}
            )
        )

    expiry = _explicit_expiry(pool)
    if not expiry and eff and term_len:
        expiry = normalize.add_duration(eff, term_len)
    if expiry:
        terms.append(
            TermResult(
                "expiry_date", "Expiry date", expiry.isoformat(), {"date": expiry.isoformat()}
            )
        )
    return terms


def _renewal_period(sentence: str) -> dict | None:
    """Duration that follows the renewal wording ("renew for successive one (1) year periods")."""
    m = re.search(r"renew|successive|sucesiv|renouvel|verlänger", sentence, re.I)
    tail = sentence[m.start() :] if m else sentence
    for _, _, d in normalize.find_durations(tail):
        if d["days"] >= 28:
            return d
    return None


def _explicit_expiry(pool) -> date | None:
    for s, _ in pool:
        m = re.search(
            r"(?:expire|terminate|until|ending on|through)\s+(?:on\s+)?("
            + normalize.DATE_RE.pattern
            + ")",
            s,
            re.I,
        )
        if m:
            return normalize.parse_date(m.group(1))
    return None


def _liability_cap(clauses: list[ExtractedClause]) -> TermResult:
    if not clauses:
        return TermResult(
            "liability_cap",
            "Liability cap",
            "Missing (no limitation of liability clause)",
            {"present": False, "reason": "no_clause"},
        )
    for s, c in _sentences_of(clauses):
        low = s.lower()
        if re.search(r"unlimited liability|shall not be limited|without (?:any )?limit", low):
            return TermResult(
                "liability_cap",
                "Liability cap",
                "Unlimited",
                {"present": None, "unlimited": True},
                s,
                c.page,
            )
        if not re.search(
            r"shall not exceed|not to exceed|limited to|in no event[^.]*exceed|aggregate liability|maximum liability|\bcap\b"
            r"|no exceder|no podrá exceder|limitad[ao] a|ne (?:pourra |saurait )?(?:dépasser|excéder)|limitée à|nicht übersteig|begrenzt auf",
            low,
        ):
            continue
        m = re.search(
            r"(\w+|\d+(?:\.\d+)?)\s*(?:\(\d+(?:\.\d+)?\)\s*)?(?:times|x)\s+(?:the\s+)?(?:total\s+|annual\s+|aggregate\s+)?(?:fees|amounts?)",
            low,
        )
        if m:
            mult = normalize.parse_number_word(m.group(1)) or 1.0
            return TermResult(
                "liability_cap",
                "Liability cap",
                f"{mult:g}x fees",
                {"present": True, "multiple_of_fees": mult},
                s,
                c.page,
            )
        if re.search(
            r"(?:fees|amounts?) (?:actually )?(?:paid|payable)|honorarios pagados|honoraires (?:payés|versés)|gezahlten? vergütung",
            low,
        ):
            months = normalize.parse_duration(low)
            mult = (
                round(months["days"] / 365, 2)
                if months and months["unit"] in {"month", "year"}
                else 1.0
            )
            span = f" ({normalize.format_duration(months)} of fees)" if months else ""
            return TermResult(
                "liability_cap",
                "Liability cap",
                f"{mult:g}x fees{span}",
                {"present": True, "multiple_of_fees": mult, "lookback": months},
                s,
                c.page,
            )
        a = normalize.parse_amount(s)
        if a:
            return TermResult(
                "liability_cap",
                "Liability cap",
                f"{a['currency']} {a['value']:,.0f}",
                {"present": True, "amount": a},
                s,
                c.page,
            )
    return TermResult(
        "liability_cap",
        "Liability cap",
        "Missing (liability clause has no cap)",
        {"present": False, "reason": "no_cap_language"},
        clauses[0].text[:300],
        clauses[0].page,
    )


def as_dict(terms: list[TermResult]) -> dict[str, TermResult]:
    return {t.key: t for t in terms}
