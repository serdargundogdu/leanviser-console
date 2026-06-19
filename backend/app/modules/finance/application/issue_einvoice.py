"""'e-Fatura kesme' use case'i (application katmanı).

Onaylı bir domain Invoice'u UBL-TR e-Fatura girdisine (EInvoiceRequest) eşler ve
EInvoiceGateway port'u üzerinden entegratöre gönderir. Profil (e-Fatura vs
e-Arşiv) alıcının kayıtlı e-Fatura mükellefi olup olmadığına göre belirlenir.
HTTP/DB bilmez; port'a bağımlıdır (adapters -> application -> domain).

Domain Invoice e-Fatura için gereken müşteri vergi kimliği/adresini taşımaz
(KVKK gereği minimal); bu bilgiler kesme anında command ile verilir. Gönderici
(LeanViser) kimliği de dışarıdan (config) gelir.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.modules.finance.application.einvoice_gateway import EInvoiceGateway
from app.modules.finance.application.einvoice_models import (
    EInvoiceLine,
    EInvoiceRequest,
    EInvoiceSendResult,
    Party,
)
from app.modules.finance.domain.invoice import Invoice, InvoiceStatus

_EINVOICE_PROFILE = "TICARIFATURA"  # kayıtlı e-Fatura mükellefi (B2B)
_EARCHIVE_PROFILE = "EARSIVFATURA"  # kayıtsız alıcı / nihai tüketici (B2C)
_DEFAULT_UNIT_CODE = "C62"  # adet — domain kalemde birim kodu tutulmaz


class EInvoiceIssueError(Exception):
    """Fatura e-Fatura olarak kesilemez (ör. onaylı değil)."""


@dataclass(frozen=True)
class IssueEInvoiceCommand:
    """Kesme girdisi: müşteri/gönderici kimliği, resmi GİB numarası, alıcı etiketi."""

    customer: Party
    supplier: Party
    gib_number: str  # resmi 16 haneli GİB fatura numarası (cbc:ID)
    customer_alias: str | None = None


class IssueEInvoice:
    """Onaylı Invoice'u entegratöre e-Fatura/e-Arşiv olarak kesen use case."""

    def __init__(self, gateway: EInvoiceGateway) -> None:
        self._gateway = gateway

    def execute(self, invoice: Invoice, command: IssueEInvoiceCommand) -> EInvoiceSendResult:
        if invoice.status is not InvoiceStatus.Approved:
            raise EInvoiceIssueError("Yalnız onaylı fatura e-Fatura olarak kesilebilir")
        # Alıcının kayıtlı PK etiketleri varsa e-Fatura (etiketi otomatik seç),
        # yoksa e-Arşiv. Verilen customer_alias her zaman önceliklidir.
        aliases = self._gateway.get_recipient_aliases(command.customer.tax_id)
        if aliases:
            profile = _EINVOICE_PROFILE
            customer_alias = command.customer_alias or aliases[0]
        else:
            profile = _EARCHIVE_PROFILE
            customer_alias = command.customer_alias
        request = EInvoiceRequest(
            number=command.gib_number,  # resmi GİB numarası -> cbc:ID
            uuid=str(uuid.uuid4()),
            issue_date=invoice.issue_date,
            currency=invoice.currency.code,
            profile=profile,
            invoice_type="SATIS",
            supplier=command.supplier,
            customer=command.customer,
            lines=tuple(
                EInvoiceLine(
                    name=line.description,
                    quantity=line.quantity,
                    unit_code=_DEFAULT_UNIT_CODE,
                    unit_price=line.unit_price.amount,
                    vat_rate=line.vat_rate.rate,
                )
                for line in invoice.lines
            ),
        )
        # LocalDocumentId = iç fatura id (izlenebilirlik); cbc:ID = resmi numara.
        return self._gateway.send_invoice(
            request, customer_alias=customer_alias, local_document_id=invoice.id
        )
