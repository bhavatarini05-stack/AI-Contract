"""Obligation tracking: expiry, renewal-notice deadlines, payment and other duties."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.pipeline import normalize
from app.pipeline.clauses import ExtractedClause
from app.pipeline.sections import sentences
from app.pipeline.terms import TermResult

ALERT_THRESHOLDS = (90, 60, 30, 7, 1, 0)

_DUTY_RE = re.compile(
    r"\b(?:shall|must|agrees? to|is required to)\s+(?:promptly\s+)?"
    r"(?:notify|provide|deliver|submit|pay|maintain|furnish|send|return|destroy|report|give)\b",
    re.I,
)


@dataclass
class ObligationResult:
    kind: str
    description: str
    due_date: date | None = None
    page: int | None = None


def derive(terms: dict[str, TermResult], clauses: list[ExtractedClause]) -> list[ObligationResult]:
    out: list[ObligationResult] = []
    expiry = (
        date.fromisoformat(terms["expiry_date"].value["date"]) if "expiry_date" in terms else None
    )
    notice = terms.get("notice_period")
    auto = terms.get("auto_renew")
    is_auto = bool(auto and auto.value.get("auto_renew"))

    if expiry:
        out.append(
            ObligationResult(
                "expiry",
                f"Contract {'renews automatically' if is_auto else 'expires'} on {expiry:%B %d, %Y}.",
                expiry,
            )
        )
    if expiry and notice and notice.value.get("days"):
        deadline = normalize.subtract_duration(expiry, notice.value)
        what = "Renewal (non-renewal) notice" if is_auto else "Termination / non-renewal notice"
        out.append(
            ObligationResult(
                "renewal_notice",
                f"{what} must be sent by {deadline:%B %d, %Y} "
                f"({normalize.format_duration(notice.value)} before {expiry:%B %d, %Y}).",
                deadline,
                notice.page,
            )
        )
    if "payment_terms" in terms:
        pt = terms["payment_terms"]
        out.append(
            ObligationResult(
                "payment", f"Invoices are payable within {pt.value['days']} days.", None, pt.page
            )
        )

    seen = set()
    for c in clauses:
        for s in sentences(c.text):
            if len(out) >= 25:
                break
            if _DUTY_RE.search(s) and normalize.parse_duration(s) and 30 < len(s) < 400:
                key = s[:80].lower()
                if key not in seen:
                    seen.add(key)
                    out.append(ObligationResult("other", s, None, c.page))
    return out


def alert_for(due: date, today: date, already: set[int]) -> int | None:
    """Return the alert threshold (days) to fire now, or None. -1 means overdue."""
    days_left = (due - today).days
    if days_left < 0:
        return -1 if -1 not in already else None
    crossed = [t for t in ALERT_THRESHOLDS if days_left <= t]
    if not crossed:
        return None
    t = min(crossed)
    return t if t not in already else None


def alert_message(kind: str, description: str, due: date, today: date) -> str:
    days = (due - today).days
    when = (
        "today"
        if days == 0
        else "tomorrow"
        if days == 1
        else f"in {days} days"
        if days > 0
        else f"{-days} days ago"
    )
    if kind == "expiry":
        return f"This contract expires {when} ({due:%b %d, %Y})."
    if kind == "renewal_notice":
        return f"Renewal notice deadline is {when} ({due:%b %d, %Y}). {description}"
    return f"Obligation due {when}: {description}"
