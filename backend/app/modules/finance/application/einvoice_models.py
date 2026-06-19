"""e-Fatura girdi modelleri (application).

Domain Invoice e-Fatura için yetersiz olduğundan (alıcı VKN/adres, gönderici,
profil, kalem KDV'si yok) UBL-TR üretimi için zengin, ayrı bir girdi modeli.
Saf VO'lar; framework-süz, Decimal (float yok).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
    first_name: str = ""  # gerçek kişi (TCKN) için ad
    family_name: str = ""  # gerçek kişi (TCKN) için soyad

    @property
    def scheme_id(self) -> str:
        return "TCKN" if len(self.tax_id) == 11 else "VKN"

    @property
    def is_person(self) -> bool:
        """Gerçek kişi mi? (TCKN -> UBL Person; VKN -> PartyName)"""
        return self.scheme_id == "TCKN"

    @property
    def person_names(self) -> tuple[str, str]:
        """(ad, soyad): açık alanlar verilmişse onlar; yoksa name son boşluktan bölünür."""
        if self.first_name or self.family_name:
            return self.first_name, self.family_name
        parts = self.name.split()
        if len(parts) >= 2:
            return " ".join(parts[:-1]), parts[-1]
        return self.name, self.name


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
    profile: str  # EARSIVFATURA / TICARIFATURA / TEMELFATURA
    invoice_type: str  # SATIS
    supplier: Party
    customer: Party
    lines: tuple[EInvoiceLine, ...]
    issue_time: str = "00:00:00"  # UBL-TR IssueTime (HH:MM:SS)


@dataclass(frozen=True)
class EInvoiceSendResult:
    """Entegratör gönderim sonucu."""

    succeeded: bool
    message: str = ""
    invoice_id: str | None = None  # entegratörün döndürdüğü belge kimliği
    ettn: str | None = None  # ETTN (UUID)


@dataclass(frozen=True)
class EInvoiceStatusLog:
    """Faturanın entegratör/GİB işleme günlüğü satırı."""

    created_at: datetime
    message: str
    type: int  # entegratör log türü (ör. 2=bilgi, 6=hata)


@dataclass(frozen=True)
class InboxInvoice:
    """Gelen kutusundaki (bize gelen) bir e-Fatura özeti."""

    document_id: str  # entegratör GUID — PDF/işlem id'si
    number: str  # GİB fatura numarası
    sender_title: str  # gönderen unvanı
    sender_tax_id: str  # gönderen VKN/TCKN
    status: str
    payable_amount: Decimal
    currency: str
    issue_date: datetime


@dataclass(frozen=True)
class InboxInvoicePage:
    """Gelen kutusu sayfalı yanıtı."""

    items: tuple[InboxInvoice, ...]
    total_count: int
    page_index: int
    page_size: int


@dataclass(frozen=True)
class EInvoiceStatus:
    """Kesilmiş faturanın güncel durumu + işleme günlükleri.

    SendInvoice'ın IsSucceded=true dönmesi yalnız kuyruğa kabulü gösterir; GİB
    şema/asenkron kontrolünün sonucu (ör. 'Error') burada görünür.
    """

    invoice_id: str  # entegratör belge kimliği (ETTN)
    local_document_id: str  # bizim fatura no
    status: str  # entegratör durumu (ör. Succeed / Error / Waiting)
    status_code: int
    message: str
    logs: tuple[EInvoiceStatusLog, ...] = ()
