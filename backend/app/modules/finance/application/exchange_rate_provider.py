"""ExchangeRateProvider port'u (application katmanı).

Hexagonal port: uygulama, döviz kurunu bu arayüz üzerinden ister. Bağımlılık
içe akar (adapters -> application -> domain). Somut implementasyon (TCMB ACL
adapter'ı) sonraki dilimde gelir — burada YOK.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency


class ExchangeRateProvider(Protocol):
    """Belirli bir tarih için base -> quote döviz kurunu döndüren port."""

    def get_rate(self, base: Currency, quote: Currency, as_of: date) -> ExchangeRate:
        """İlgili kuru döndürür. Somut karşılığı adapter katmanındadır."""
        ...
