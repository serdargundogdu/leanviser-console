"""InvoiceRepository port'u (application katmanı).

Fatura kalıcılığı için port. Somut karşılığı adapter katmanındadır (ör. SQLite).
Bağımlılık içe akar: adapters -> application -> domain.
"""

from __future__ import annotations

from typing import Protocol

from app.modules.finance.domain.invoice import Invoice


class InvoiceRepository(Protocol):
    """Fatura saklama/okuma port'u."""

    def save(self, invoice: Invoice) -> None:
        """Faturayı kaydeder; aynı id varsa üzerine yazar."""
        ...

    def get(self, invoice_id: str) -> Invoice | None:
        """id ile faturayı döndürür; yoksa None."""
        ...

    def list_all(self) -> list[Invoice]:
        """Tüm kayıtlı faturaları döndürür."""
        ...

    def delete(self, invoice_id: str) -> None:
        """Faturayı (ve varsa kaynak girdilerini) siler; yoksa sessiz geçer."""
        ...

    def save_source(self, invoice_id: str, source: dict) -> None:
        """Faturanın kaynak girdilerini (derleme isteği) saklar; varsa üzerine yazar."""
        ...

    def get_source(self, invoice_id: str) -> dict | None:
        """Faturanın kaynak girdilerini döndürür; yoksa None."""
        ...

    def next_invoice_sequence(self, series: str, year: int) -> int:
        """(seri, yıl) için bir sonraki sıra numarasını atomik olarak üretir (1'den başlar).

        GİB ardışık numaralandırması için: her çağrı bir öncekinden bir büyük,
        boşluksuz değer döndürür.
        """
        ...
