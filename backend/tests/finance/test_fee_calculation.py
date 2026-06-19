"""FeeCalculation testleri: KDV, hizmet bedeli, FX birim-önce ve hatalar."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.domain.fee_calculation import FeeCalculation
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money
from app.modules.finance.domain.vat import VatRate

FX_EUR_TRY = ExchangeRate(base=Currency.EUR, rate=Decimal("47.7841"), as_of=date(2026, 6, 19))


def test_net_amount_splits_vat():
    gross = Money(Decimal("100.00"), Currency.TRY)
    net = FeeCalculation.net_amount(gross, VatRate(Decimal("0.20")))
    assert net == Money(Decimal("83.33"), Currency.TRY)


def test_service_fee_preserves_currency():
    daily = Money(Decimal("750.00"), Currency.EUR)
    assert FeeCalculation.service_fee(daily, Decimal("16")) == Money(
        Decimal("12000.00"), Currency.EUR
    )


@pytest.mark.parametrize(
    ("daily", "days", "unit", "line"),
    [
        ("750.00", "16", "35838.08", "573409.28"),
        ("550.00", "8", "26281.26", "210250.08"),
    ],
)
def test_fx_service_fee_is_unit_first(daily, days, unit, line):
    daily_rate = Money(Decimal(daily), Currency.EUR)
    unit_try = FeeCalculation.to_try(daily_rate, FX_EUR_TRY)
    assert unit_try == Money(Decimal(unit), Currency.TRY)
    assert FeeCalculation.service_fee(unit_try, Decimal(days)) == Money(Decimal(line), Currency.TRY)
    assert FeeCalculation.invoice_line_total_try(daily_rate, Decimal(days), FX_EUR_TRY) == Money(
        Decimal(line), Currency.TRY
    )


def test_to_try_currency_mismatch():
    amount_try = Money(Decimal("100.00"), Currency.TRY)
    with pytest.raises(CurrencyMismatchError):
        FeeCalculation.to_try(amount_try, FX_EUR_TRY)


def test_non_positive_inputs_rejected():
    with pytest.raises(ValueError):
        FeeCalculation.net_amount(Money(Decimal("0.00"), Currency.TRY), VatRate(Decimal("0.20")))
    with pytest.raises(ValueError):
        FeeCalculation.service_fee(Money(Decimal("100.00"), Currency.TRY), Decimal("0"))
    with pytest.raises(ValueError):
        FeeCalculation.service_fee(Money(Decimal("100.00"), Currency.TRY), Decimal("-1"))
