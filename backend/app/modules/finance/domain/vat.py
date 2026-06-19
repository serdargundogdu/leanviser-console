"""KDV oranı değer nesnesi (saf domain)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# İzin verilen KDV oranları (Ubiquitous Language: VatRate). Genişletilebilir sabit:
# yeni bir oran iş kuralı olarak buraya eklenir. Decimal eşitliği değer-bazlı
# olduğu için "0.20" ile "0.2" aynı kabul edilir.
ALLOWED_RATES: frozenset[Decimal] = frozenset(
    {Decimal("0.00"), Decimal("0.01"), Decimal("0.10"), Decimal("0.20")}
)


@dataclass(frozen=True)
class VatRate:
    """Oransal KDV. 0 <= rate < 1 olmalı ve ALLOWED_RATES üyesi olmalı."""

    rate: Decimal

    def __post_init__(self) -> None:
        if not (Decimal(0) <= self.rate < Decimal(1)):
            raise ValueError(f"KDV oranı 0 <= rate < 1 olmalı: {self.rate}")
        if self.rate not in ALLOWED_RATES:
            raise ValueError(f"İzin verilmeyen KDV oranı: {self.rate}")
