"""VatRate birim testleri."""

from decimal import Decimal

import pytest

from app.modules.finance.domain.vat import ALLOWED_RATES, VatRate


def test_allowed_rates_accepted():
    for rate in [Decimal("0.00"), Decimal("0.01"), Decimal("0.10"), Decimal("0.20")]:
        assert VatRate(rate).rate == rate


def test_rate_out_of_range_rejected():
    with pytest.raises(ValueError):
        VatRate(Decimal("-0.01"))
    with pytest.raises(ValueError):
        VatRate(Decimal("1.00"))


def test_rate_not_in_allowed_set_rejected():
    with pytest.raises(ValueError):
        VatRate(Decimal("0.05"))


def test_allowed_rates_constant_membership():
    assert Decimal("0.20") in ALLOWED_RATES
    assert Decimal("0.05") not in ALLOWED_RATES
