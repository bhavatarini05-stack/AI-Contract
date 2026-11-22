from datetime import date

import pytest

from app.pipeline import normalize as n


@pytest.mark.parametrize(
    "text,value,unit,days",
    [
        ("sixty (60) days", 60, "day", 60),
        ("twelve (12) months", 12, "month", 365),
        ("a period of one year", 1, "year", 365),
        ("within 30 days", 30, "day", 30),
        ("ten (10) business days", 10, "day", 10),
        ("doce (12) meses", 12, "month", 365),
        ("treinta (30) días", 30, "day", 30),
        ("successive one (1) year periods", 1, "year", 365),
    ],
)
def test_parse_duration(text, value, unit, days):
    d = n.parse_duration(text)
    assert (d["value"], d["unit"], d["days"]) == (value, unit, days)


def test_parse_duration_ignores_substrings():
    assert n.parse_duration("the data month") is None
    assert n.parse_duration("no duration here") is None


def test_notice_duration_prefers_notice_over_renewal_length():
    s = (
        "This Agreement shall automatically renew for successive one (1) year periods unless either "
        "party gives written notice of non-renewal at least sixty (60) days prior to the end of the term."
    )
    assert n.notice_duration(s)["days"] == 60


@pytest.mark.parametrize(
    "text,expected",
    [
        ("January 15, 2026", date(2026, 1, 15)),
        ("15th day of January, 2026", date(2026, 1, 15)),
        ("2026-03-01", date(2026, 3, 1)),
        ("1 de marzo de 2026", date(2026, 3, 1)),
    ],
)
def test_parse_date(text, expected):
    assert n.parse_date(text) == expected


def test_add_and_subtract_duration():
    twelve_months = n.parse_duration("twelve (12) months")
    assert n.add_duration(date(2026, 1, 15), twelve_months) == date(2027, 1, 14)
    assert n.subtract_duration(date(2027, 1, 14), n.parse_duration("60 days")) == date(2026, 11, 15)


def test_parse_amount():
    assert n.parse_amount("a fee of $25,000 per month") == {
        "value": 25000.0,
        "currency": "USD",
        "text": "$25,000",
    }
    assert n.parse_amount("EUR 1.5 million")["value"] == 1_500_000
