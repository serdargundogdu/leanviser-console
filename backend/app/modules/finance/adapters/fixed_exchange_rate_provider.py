"""Sabit kur sağlayıcı (geçici adapter).

ExchangeRateProvider port'unun sabit-kur implementasyonu. İlk uçtan uca çıktı için
ağ/tarih bağımlılığı olmadan deterministik kur verir; TcmbExchangeRateProvider'a
geçiş yalnız wiring değişikliğidir (port aynı).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency

# Temsili sabit TCMB döviz alış kurları (TRY karşısı).
_FIXED_RATES: dict[Currency, Decimal] = {
    Currency.EUR: Decimal("47.7841"),
    Currency.USD: Decimal("43.1234"),
}


class FixedExchangeRateProvider(ExchangeRateProvider):
    """base -> TRY için sabit kur döndürür."""

    def get_rate(self, base: Currency, quote: Currency, as_of: date) -> ExchangeRate:
        if quote is not Currency.TRY:
            raise ValueError(f"Yalnız TRY karşısı desteklenir: {quote.code}")
        rate = _FIXED_RATES.get(base)
        if rate is None:
            raise ValueError(f"Sabit kur tanımlı değil: {base.code}")
        return ExchangeRate(base=base, rate=rate, as_of=as_of, quote=quote)
