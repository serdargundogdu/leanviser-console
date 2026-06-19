"""Döviz kuru değer nesnesi (saf domain).

İş anlamı: TCMB döviz alış (fxBuyRate). Kur burada dışarıdan verilir; gerçek
TCMB erişimi sonraki dilimde ACL/port (ExchangeRateProvider) üzerinden gelir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.modules.finance.domain.money import Currency

# Kur 4 haneye yuvarlanır (ROUND_HALF_UP).
_RATE_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True)
class ExchangeRate:
    """base -> quote dönüşüm kuru. rate pozitif, 4 haneye yuvarlanır.

    Not: quote varsayılanı TRY'dir; dataclass varsayılan-argüman sıralaması
    gereği alanlardan en sonda yer alır (yapımda anahtar-kelime ile verilir).
    """

    base: Currency
    rate: Decimal
    as_of: date
    quote: Currency = Currency.TRY

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError(f"Kur pozitif olmalı: {self.rate}")
        quantized = self.rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "rate", quantized)
