"""EInvoiceGateway port'u (application katmanı).

e-Fatura/e-Arşiv özel entegratörüyle (ör. Uyumsoft) konuşan ACL port'u. Somut
karşılığı adapters/'tadır; bağımlılık içe akar (adapters -> application -> domain).

Bu dilimde yalnız bağlantı/kimlik sağlığı ve alıcı sorgu tanımlı; fatura gönderimi
(UBL-TR üretimi + SendInvoice), durum ve PDF sonraki dilimde eklenecek.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class EInvoiceGateway(Protocol):
    """e-Fatura entegratör port'u."""

    def get_system_date(self) -> datetime:
        """Entegratör sistem tarihini döndürür (bağlantı + kimlik sağlığı)."""
        ...

    def is_einvoice_user(self, vkn_tckn: str, alias: str | None = None) -> bool:
        """Alıcı kayıtlı e-Fatura mükellefi mi? (e-Fatura vs e-Arşiv kararı)"""
        ...
