"""ExchangeRate birim testleri."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency


def test_quantizes_to_four_places_half_up():
    fx = ExchangeRate(base=Currency.EUR, rate=Decimal("47.78415"), as_of=date(2026, 6, 19))
    assert fx.rate == Decimal("47.7842")
    assert fx.quote is Currency.TRY


def test_keeps_four_places_intact():
    fx = ExchangeRate(base=Currency.EUR, rate=Decimal("47.7841"), as_of=date(2026, 6, 19))
    assert fx.rate == Decimal("47.7841")


def test_non_positive_rate_rejected():
    with pytest.raises(ValueError):
        ExchangeRate(base=Currency.EUR, rate=Decimal("0"), as_of=date(2026, 6, 19))
    with pytest.raises(ValueError):
        ExchangeRate(base=Currency.USD, rate=Decimal("-1.0"), as_of=date(2026, 6, 19))
