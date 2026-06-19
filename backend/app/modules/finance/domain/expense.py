"""Masraf (Expense) aggregate'i — KDV dahil brüt tutardan net/KDV ayrıştırması.

Ubiquitous Language eşlemesi (TR -> kod/İngilizce):
  Akaryakıt -> Fuel, Yemek -> Meal, Otopark -> Parking, Otoyol -> Toll,
  Uçak Bileti -> FlightTicket, Diğer -> Other.

İş kuralı aggregate'in kendisinde tutulur (anemik model değil). KVKK gereği
kişi değil firma tutulur; company şimdilik serbest metindir (CustomerCompany
değer nesnesi ve kalıcılık sonraki dilimde).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from app.modules.finance.domain.money import Money
from app.modules.finance.domain.vat import VatRate


class ExpenseType(Enum):
    """Masraf türü. Genişletilebilir."""

    Fuel = "Fuel"
    Meal = "Meal"
    Parking = "Parking"
    Toll = "Toll"
    FlightTicket = "FlightTicket"
    Other = "Other"


@dataclass(frozen=True)
class Expense:
    """KDV dahil brüt tutarlı masraf. net + vat == gross değişmezi korunur."""

    id: str
    gross: Money
    vat_rate: VatRate
    type: ExpenseType
    date: date
    company: str

    def __post_init__(self) -> None:
        if self.gross.amount <= 0:
            raise ValueError(f"Brüt tutar pozitif olmalı: {self.gross.amount}")

    def net_amount(self) -> Money:
        """KDV hariç net tutar: round2(gross / (1 + vat_rate))."""
        divisor = Decimal(1) + self.vat_rate.rate
        return Money(self.gross.amount / divisor, self.gross.currency)

    def vat_amount(self) -> Money:
        """KDV tutarı: gross - net (toplam korunur)."""
        return self.gross.subtract(self.net_amount())
