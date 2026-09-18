from datetime import date

from app.services.warranty_service import _add_months


def test_add_months_clamps_end_of_month():
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert _add_months(date(2026, 2, 28), 12) == date(2027, 2, 28)


def test_add_months_handles_year_boundary():
    assert _add_months(date(2026, 12, 10), 2) == date(2027, 2, 10)