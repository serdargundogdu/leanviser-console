"""invoice_serialization roundtrip testleri (ağsız)."""

from datetime import date
from decimal import Decimal

from app.modules.finance.adapters.invoice_serialization import invoice_from_dict, invoice_to_dict
from app.modules.finance.domain.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.modules.finance.domain.money import Currency, Money


def _invoice() -> Invoice:
    invoice = Invoice(
        id="INV-1",
        customer_company="ACME",
        currency=Currency.TRY,
        issue_date=date(2026, 6, 19),
    )
    invoice.add_line(
        InvoiceLine(
            description="Hizmet",
            unit_price=Money(Decimal("35838.08"), Currency.TRY),
            quantity=Decimal("16"),
        )
    )
    invoice.approve()
    return invoice


def test_roundtrip_preserves_invoice():
    original = _invoice()
    restored = invoice_from_dict(invoice_to_dict(original))
    assert restored.id == original.id
    assert restored.customer_company == "ACME"
    assert restored.currency is Currency.TRY
    assert restored.status is InvoiceStatus.Approved
    assert restored.total() == Money(Decimal("573409.28"), Currency.TRY)
    assert len(restored.lines) == 1
    assert restored.lines[0].description == "Hizmet"


def test_to_dict_is_json_friendly():
    data = invoice_to_dict(_invoice())
    assert data["currency"] == "TRY"
    assert data["status"] == "Approved"
    assert data["lines"][0]["unit_price"] == "35838.08"
