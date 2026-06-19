"""EInvoiceGateway port'u (application katmanı).

e-Fatura/e-Arşiv özel entegratörüyle (ör. Uyumsoft) konuşan ACL port'u. Somut
karşılığı adapters/'tadır; bağımlılık içe akar (adapters -> application -> domain).

Bağlantı/kimlik sağlığı, alıcı sorgu ve fatura gönderimi (UBL-TR + SendInvoice)
tanımlı; durum sorgu ve PDF sonraki dilimde eklenecek.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.finance.application.einvoice_models import EInvoiceRequest, EInvoiceSendResult


class EInvoiceGateway(Protocol):
    """e-Fatura entegratör port'u."""

    def get_system_date(self) -> datetime:
        """Entegratör sistem tarihini döndürür (bağlantı + kimlik sağlığı)."""
        ...

    def is_einvoice_user(self, vkn_tckn: str, alias: str | None = None) -> bool:
        """Alıcı kayıtlı e-Fatura mükellefi mi? (e-Fatura vs e-Arşiv kararı)"""
        ...

    def send_invoice(
        self,
        req: EInvoiceRequest,
        *,
        customer_alias: str | None = None,
        local_document_id: str | None = None,
    ) -> EInvoiceSendResult:
        """Faturayı entegratöre gönderir (UBL-TR üretip iletir).

        İş kuralı reddini (IsSucceded=false) `succeeded=False` + mesaj olarak
        döndürür; taşıma/SOAP hatalarında istisna atar.
        """
        ...
