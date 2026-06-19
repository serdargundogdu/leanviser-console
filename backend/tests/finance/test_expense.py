"""Expense KDV ayrıştırma testleri: net + vat == gross her vakada."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.domain.expense import Expense, ExpenseType
from app.modules.finance.domain.money import Currency, Money
from app.modules.finance.domain.vat import VatRate


def _expense(gross: str, rate: str) -> Expense:
    return Expense(
        id="E-1",
        gross=Money(Decimal(gross), Currency.TRY),
        vat_rate=VatRate(Decimal(rate)),
        type=ExpenseType.Fuel,
        date=date(2026, 6, 19),
        company="ACME",
    )


@pytest.mark.parametrize(
    ("gross", "rate", "net", "vat"),
    [
        ("120.00", "0.20", "100.00", "20.00"),
        ("110.00", "0.10", "100.00", "10.00"),
        ("100.00", "0.20", "83.33", "16.67"),
        ("50.00", "0.01", "49.50", "0.50"),
    ],
)
def test_vat_split_preserves_total(gross, rate, net, vat):
    expense = _expense(gross, rate)
    assert expense.net_amount() == Money(Decimal(net), Currency.TRY)
    assert expense.vat_amount() == Money(Decimal(vat), Currency.TRY)
    assert expense.net_amount().add(expense.vat_amount()) == Money(Decimal(gross), Currency.TRY)


def test_non_positive_gross_rejected():
    with pytest.raises(ValueError):
        _expense("0.00", "0.20")
    with pytest.raises(ValueError):
        _expense("-10.00", "0.20")
