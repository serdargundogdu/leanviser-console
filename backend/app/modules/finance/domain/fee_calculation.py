"""Bedel Hesaplama — durumsuz domain servisi (saf domain).

KDV ayrıştırma, hizmet bedeli ve TRY'ye dönüşüm. Tüm para yuvarlaması Money,
kur yuvarlaması ExchangeRate içinde merkezîdir. Fatura kalemi için "birim-önce"
kuralı invoice_line_total_try'de kodlanır: önce birim TRY'ye yuvarlanır, sonra
gün ile çarpılır.
"""

from __future__ import annotations

from decimal import Decimal

from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import CurrencyMismatchError, Money
from app.modules.finance.domain.vat import VatRate


class FeeCalculation:
    """Durumsuz hesaplama servisi; tüm metotlar yan etkisiz ve statiktir."""

    @staticmethod
    def net_amount(gross: Money, rate: VatRate) -> Money:
        """KDV hariç net: round2(gross / (1 + rate)). gross pozitif olmalı."""
        if gross.amount <= 0:
            raise ValueError(f"Brüt tutar pozitif olmalı: {gross.amount}")
        divisor = Decimal(1) + rate.rate
        return Money(gross.amount / divisor, gross.currency)

    @staticmethod
    def service_fee(daily_rate: Money, days: Decimal) -> Money:
        """Hizmet bedeli: daily_rate × days. currency korunur; days pozitif."""
        if days <= 0:
            raise ValueError(f"Gün sayısı pozitif olmalı: {days}")
        return daily_rate.multiply(days)

    @staticmethod
    def to_try(amount: Money, fx: ExchangeRate) -> Money:
        """Tutarı kur ile quote birimine (TRY) çevirir: round2(amount × rate)."""
        if amount.currency is not fx.base:
            raise CurrencyMismatchError(
                f"Kur tabanı {fx.base.code} ile tutar {amount.currency.code} uyuşmuyor"
            )
        return Money(amount.amount * fx.rate, fx.quote)

    @staticmethod
    def invoice_line_total_try(daily_rate: Money, days: Decimal, fx: ExchangeRate) -> Money:
        """Birim-önce fatura kalemi toplamı: round2(daily_rate × rate) sonra × days."""
        unit_try = FeeCalculation.to_try(daily_rate, fx)
        return FeeCalculation.service_fee(unit_try, days)
