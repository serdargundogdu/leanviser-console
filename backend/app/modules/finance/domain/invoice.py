"""Fatura (Invoice) aggregate'i — saf domain.

Invoice durumu olan bir aggregate root'tur: kalemleri tutar, toplamı hesaplar,
tüm kalemlerin aynı para biriminde olmasını zorlar ve Draft -> Approved -> Sent
durum makinesini yönetir. Hesaplama (FX birim-önce, KDV ayrıştırma) bu aggregate'e
girmez; kalemler dışarıda (FeeCalculation/use case) hesaplanıp eklenir.

Ubiquitous Language: Fatura/kalem/durum -> Invoice/InvoiceLine/InvoiceStatus
(Draft -> Approved -> Sent). "Fatura Taslağı" = Draft durumu; "Onay" = approve().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money
from app.modules.finance.domain.vat import VatRate

# Açıkça verilmeyen ya da eski (KDV oranı yazılmadan kaydedilmiş) kalemler için
# varsayılan genel KDV oranı. Yeni kalemler oranı her zaman açıkça taşır.
_DEFAULT_VAT_RATE = Decimal("0.20")


class InvoiceStateError(Exception):
    """Geçersiz durum geçişi ya da mevcut durumda yasak işlem denendiğinde fırlatılır."""


class InvoiceStatus(Enum):
    """Fatura durumu. İzinli ilerleme: Draft -> Approved -> Sent."""

    Draft = "Draft"
    Approved = "Approved"
    Sent = "Sent"


@dataclass(frozen=True)
class InvoiceLine:
    """Fatura kalemi (değer nesnesi). line_total = unit_price × quantity (net).

    Hizmet kaleminde quantity = consultantDays, unit_price = (TRY'ye çevrilmiş)
    dailyRate; masraf kaleminde quantity = 1, unit_price = net tutar. unit_price
    KDV hariçtir; KDV oranı kalem üzerinde tutulur (vat_amount net üzerinden).
    """

    description: str
    unit_price: Money
    quantity: Decimal
    vat_rate: VatRate = field(default_factory=lambda: VatRate(_DEFAULT_VAT_RATE))

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"Kalem miktarı pozitif olmalı: {self.quantity}")
        if self.unit_price.amount <= 0:
            raise ValueError(f"Birim fiyat pozitif olmalı: {self.unit_price.amount}")

    def line_total(self) -> Money:
        """Net kalem tutarı (KDV hariç)."""
        return self.unit_price.multiply(self.quantity)

    def vat_amount(self) -> Money:
        """Kalemin KDV tutarı (net × oran)."""
        return self.line_total().multiply(self.vat_rate.rate)


class Invoice:
    """Fatura aggregate root'u. Kimlik-bazlı eşitlik; durumu değişebilir.

    Tüm kalemler faturanın currency'sinde olmalıdır. Kalem yalnız Draft durumunda
    eklenebilir; boş fatura onaylanamaz; yalnız onaylı fatura gönderilebilir.
    """

    def __init__(
        self, id: str, customer_company: str, currency: Currency, issue_date: date
    ) -> None:
        self.id = id
        self.customer_company = customer_company
        self.currency = currency
        self.issue_date = issue_date
        self._status = InvoiceStatus.Draft
        self._lines: list[InvoiceLine] = []
        # Resmi GİB fatura numarası (16 hane); e-Fatura kesilirken atanır.
        self.gib_number: str | None = None
        # Entegratörce atanan ETTN (e-belge kimliği); gönderildiğinde dolar.
        self.ettn: str | None = None

    @classmethod
    def reconstitute(
        cls,
        id: str,
        customer_company: str,
        currency: Currency,
        issue_date: date,
        status: InvoiceStatus,
        lines: list[InvoiceLine],
        gib_number: str | None = None,
        ettn: str | None = None,
    ) -> Invoice:
        """Kalıcılıktan yeniden kurar; durum/kalemleri doğrudan yükler.

        Durum makinesi invariant'larını bilinçli olarak atlar — yalnız repository
        rehydration içindir, iş akışında kullanılmaz.
        """
        invoice = cls(id, customer_company, currency, issue_date)
        invoice._status = status
        invoice._lines = list(lines)
        invoice.gib_number = gib_number
        invoice.ettn = ettn
        return invoice

    @property
    def status(self) -> InvoiceStatus:
        return self._status

    @property
    def lines(self) -> tuple[InvoiceLine, ...]:
        """Kalemlerin o anki değişmez (snapshot) görünümü."""
        return tuple(self._lines)

    def add_line(self, line: InvoiceLine) -> None:
        """Taslak faturaya kalem ekler; currency tutarlılığını zorlar."""
        if self._status is not InvoiceStatus.Draft:
            raise InvoiceStateError("Yalnız taslak (Draft) faturaya kalem eklenebilir")
        if line.unit_price.currency is not self.currency:
            raise CurrencyMismatchError(
                f"Kalem {line.unit_price.currency.code}, fatura {self.currency.code}"
            )
        self._lines.append(line)

    def total(self) -> Money:
        """Net toplam (KDV hariç kalem toplamlarının toplamı; kalem yoksa sıfır)."""
        running_total = Money(Decimal(0), self.currency)
        for line in self._lines:
            running_total = running_total.add(line.line_total())
        return running_total

    def vat_total(self) -> Money:
        """Toplam KDV (kalem KDV'lerinin toplamı)."""
        running_total = Money(Decimal(0), self.currency)
        for line in self._lines:
            running_total = running_total.add(line.vat_amount())
        return running_total

    def gross_total(self) -> Money:
        """Brüt toplam (net + KDV)."""
        return self.total().add(self.vat_total())

    def approve(self) -> None:
        """Draft -> Approved. Boş fatura onaylanamaz."""
        if self._status is not InvoiceStatus.Draft:
            raise InvoiceStateError("Yalnız taslak fatura onaylanabilir")
        if not self._lines:
            raise InvoiceStateError("Boş fatura onaylanamaz")
        self._status = InvoiceStatus.Approved

    def send(self, ettn: str | None = None) -> None:
        """Approved -> Sent. Entegratörle kesildiyse ETTN birlikte kaydedilir."""
        if self._status is not InvoiceStatus.Approved:
            raise InvoiceStateError("Yalnız onaylı fatura gönderilebilir")
        self._status = InvoiceStatus.Sent
        if ettn is not None:
            self.ettn = ettn

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Invoice) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)
