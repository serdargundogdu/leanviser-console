"""e-Fatura girdi modelleri (application).

Domain Invoice e-Fatura için yetersiz olduğundan (alıcı VKN/adres, gönderici,
profil, kalem KDV'si yok) UBL-TR üretimi için zengin, ayrı bir girdi modeli.
Saf VO'lar; framework-süz, Decimal (float yok).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Party:
    """Fatura tarafı (gönderici/alıcı)."""

    tax_id: str  # VKN (10 hane) veya TCKN (11 hane)
    name: str  # unvan ya da ad soyad
    tax_office: str = ""  # vergi dairesi (tüzel kişi)
    country: str = "Türkiye"
    city: str = ""
    district: str = ""
    street: str = ""

    @property
    def scheme_id(self) -> str:
        return "TCKN" if len(self.tax_id) == 11 else "VKN"


@dataclass(frozen=True)
class EInvoiceLine:
    """Fatura kalemi (KDV hariç birim fiyat + oran)."""

    name: str
    quantity: Decimal
    unit_code: str  # UN/ECE (ör. C62=adet, DAY=gün)
    unit_price: Decimal  # KDV hariç birim fiyat
    vat_rate: Decimal  # ör. 0.20

    def net(self) -> Decimal:
        return self.unit_price * self.quantity

    def vat(self) -> Decimal:
        return self.net() * self.vat_rate


@dataclass(frozen=True)
class EInvoiceRequest:
    """UBL-TR üretimi için tam e-Fatura girdisi."""

    number: str  # GİB fatura no (ör. ABC2026000000001)
    uuid: str  # ETTN
    issue_date: date
    currency: str  # TRY
    profile: str  # EARSIVFATURA / TEMELFATURA
    invoice_type: str  # SATIS
    supplier: Party
    customer: Party
    lines: tuple[EInvoiceLine, ...]
