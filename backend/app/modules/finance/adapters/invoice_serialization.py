"""Invoice <-> dict serileştirme (kalıcılık adapter'ları arasında ortak).

SQLite ve Postgres adapter'ları faturayı bu yardımcılarla JSON-uyumlu dict'e çevirir
ve geri kurar. Tutarlar string tutulur (Decimal kesinliği). Domain JSON bilmez;
serileştirme adapter katmanındadır.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.modules.finance.domain.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.modules.finance.domain.money import Currency, Money
from app.modules.finance.domain.vat import VatRate

# KDV oranı yazılmadan kaydedilmiş eski kalemler için varsayılan (genel oran).
_DEFAULT_VAT_RATE = "0.20"


def invoice_to_dict(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "customer_company": invoice.customer_company,
        "currency": invoice.currency.code,
        "issue_date": invoice.issue_date.isoformat(),
        "status": invoice.status.value,
        "gib_number": invoice.gib_number,
        "ettn": invoice.ettn,
        "lines": [
            {
                "description": line.description,
                "unit_price": str(line.unit_price.amount),
                "currency": line.unit_price.currency.code,
                "quantity": str(line.quantity),
                "vat_rate": str(line.vat_rate.rate),
            }
            for line in invoice.lines
        ],
    }


def invoice_from_dict(data: dict) -> Invoice:
    lines = [
        InvoiceLine(
            description=line["description"],
            unit_price=Money(Decimal(line["unit_price"]), Currency[line["currency"]]),
            quantity=Decimal(line["quantity"]),
            vat_rate=VatRate(Decimal(line.get("vat_rate", _DEFAULT_VAT_RATE))),
        )
        for line in data["lines"]
    ]
    return Invoice.reconstitute(
        id=data["id"],
        customer_company=data["customer_company"],
        currency=Currency[data["currency"]],
        issue_date=date.fromisoformat(data["issue_date"]),
        status=InvoiceStatus(data["status"]),
        lines=lines,
        gib_number=data.get("gib_number"),
        ettn=data.get("ettn"),
    )
