"""Money ve Currency birim testleri (framework-süz)."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money


def test_quantizes_to_two_places_half_up():
    assert Money(Decimal("100.005"), Currency.TRY).amount == Decimal("100.01")
    assert Money(Decimal("100"), Currency.TRY).amount == Decimal("100.00")


def test_value_based_equality_and_frozen():
    assert Money(Decimal("100.00"), Currency.TRY) == Money(Decimal("100"), Currency.TRY)
    money = Money(Decimal("10.00"), Currency.EUR)
    with pytest.raises(FrozenInstanceError):
        money.amount = Decimal("20.00")


def test_add_subtract_preserve_currency():
    a = Money(Decimal("100.00"), Currency.TRY)
    b = Money(Decimal("20.00"), Currency.TRY)
    assert a.add(b) == Money(Decimal("120.00"), Currency.TRY)
    assert a.subtract(b) == Money(Decimal("80.00"), Currency.TRY)
    assert a.add(b).currency is Currency.TRY


def test_multiply_by_scalar_decimal_and_int():
    unit = Money(Decimal("35838.08"), Currency.TRY)
    assert unit.multiply(Decimal("16")) == Money(Decimal("573409.28"), Currency.TRY)
    assert unit.multiply(16) == Money(Decimal("573409.28"), Currency.TRY)


def test_currency_mismatch_on_add_and_subtract():
    eur = Money(Decimal("100.00"), Currency.EUR)
    try_ = Money(Decimal("100.00"), Currency.TRY)
    with pytest.raises(CurrencyMismatchError):
        eur.add(try_)
    with pytest.raises(CurrencyMismatchError):
        eur.subtract(try_)


def test_currency_minor_units_and_code():
    assert Currency.TRY.minor_units == 2
    assert Currency.EUR.minor_units == 2
    assert Currency.USD.minor_units == 2
    assert Currency.TRY.code == "TRY"
