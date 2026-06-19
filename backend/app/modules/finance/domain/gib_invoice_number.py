"""GİB fatura numarası değer nesnesi (saf domain).

16 hane: 3 büyük harf (seri) + 4 hane yıl + 9 hane sıra. Örn: LVS2026000000001.
GİB e-Fatura/e-Arşiv UBL şeması cbc:ID için bu formatı zorunlu kılar; geçersiz
numara entegratör tarafında şema (schematron) kontrolünde reddedilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERN = re.compile(r"^[A-Z]{3}\d{4}\d{9}$")  # seri(3) + yıl(4) + sıra(9)
_MAX_SEQUENCE = 999_999_999  # 9 hane


@dataclass(frozen=True)
class GibInvoiceNumber:
    """16 haneli GİB fatura numarası (değer nesnesi)."""

    value: str

    def __post_init__(self) -> None:
        if not _PATTERN.match(self.value):
            raise ValueError(
                f"Geçersiz GİB fatura numarası: {self.value!r} "
                "(ABC2026000000001 — 3 harf + yıl + 9 hane sıra bekleniyor)"
            )

    @classmethod
    def from_parts(cls, series: str, year: int, sequence: int) -> GibInvoiceNumber:
        """Seri + yıl + sıra'dan numara üretir (sıra 9 haneye sıfır-doldurulur)."""
        if not (len(series) == 3 and series.isascii() and series.isalpha() and series.isupper()):
            raise ValueError(f"Seri 3 büyük harf (A-Z) olmalı: {series!r}")
        if not (1000 <= year <= 9999):
            raise ValueError(f"Yıl 4 hane olmalı: {year}")
        if not (1 <= sequence <= _MAX_SEQUENCE):
            raise ValueError(f"Sıra 1..{_MAX_SEQUENCE} aralığında olmalı: {sequence}")
        return cls(f"{series}{year}{sequence:09d}")

    @property
    def series(self) -> str:
        return self.value[:3]

    @property
    def year(self) -> int:
        return int(self.value[3:7])

    @property
    def sequence(self) -> int:
        return int(self.value[7:])
