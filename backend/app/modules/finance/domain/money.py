"""Para birimi ve Money değer nesnesi (saf domain).

Bu modül framework bilmez. Tüm tutarlar Decimal'dir (float YASAK); yuvarlama
ROUND_HALF_UP ile para biriminin minor_units hanesine yapılır. Money değişmez
(frozen) ve değer-bazlı eşitliğe sahiptir.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class CurrencyMismatchError(Exception):
    """Farklı para birimleri arasında aritmetik denendiğinde fırlatılır."""


class Currency(Enum):
    """ISO 4217 para birimleri. Her biri minor_units (ondalık hane) taşır."""

    TRY = ("TRY", 2)
    EUR = ("EUR", 2)
    USD = ("USD", 2)

    def __init__(self, code: str, minor_units: int) -> None:
        self.code = code
        self.minor_units = minor_units


@dataclass(frozen=True)
class Money:
    """Bir para birimindeki tutar. Değişmez; değer-bazlı eşitlik.

    amount kuruluşta minor_units hanesine ROUND_HALF_UP ile yuvarlanır; böylece
    "2 hane" değişmezi her zaman korunur ve eşitlik kanoniktir. Aritmetik yalnız
    aynı currency ile yapılır; aksi hâlde CurrencyMismatchError.
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        quantized = self.amount.quantize(self._quantum, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)

    @property
    def _quantum(self) -> Decimal:
        """Para biriminin minor_units hanesine karşılık gelen yuvarlama adımı."""
        return Decimal(1).scaleb(-self.currency.minor_units)

    def _ensure_same_currency(self, other: Money) -> None:
        if self.currency is not other.currency:
            raise CurrencyMismatchError(
                f"{self.currency.code} ile {other.currency.code} birleştirilemez"
            )

    def add(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, scalar: Decimal | int) -> Money:
        """Tutarı bir skaler ile çarpar; currency korunur, sonuç yuvarlanır."""
        return Money(self.amount * scalar, self.currency)
