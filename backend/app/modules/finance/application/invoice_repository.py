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
