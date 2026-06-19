"""invoice_serialization roundtrip testleri (ağsız)."""

from datetime import date
from decimal import Decimal

from app.modules.finance.adapters.invoice_serialization import invoice_from_dict, invoice_to_dict
from app.modules.finance.domain.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.modules.finance.domain.money import Currency, Money
from app.modules.finance.domain.vat import VatRate


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
    assert data["lines"][0]["vat_rate"] == "0.20"


def test_roundtrip_preserves_vat_rate():
    invoice = Invoice(
        id="INV-2",
        customer_company="ACME",
        currency=Currency.TRY,
        issue_date=date(2026, 6, 19),
    )
    invoice.add_line(
        InvoiceLine(
            description="Hizmet",
            unit_price=Money(Decimal("1000.00"), Currency.TRY),
            quantity=Decimal("1"),
            vat_rate=VatRate(Decimal("0.10")),
        )
    )
    restored = invoice_from_dict(invoice_to_dict(invoice))
    assert restored.lines[0].vat_rate == VatRate(Decimal("0.10"))


def test_legacy_line_without_vat_rate_defaults_to_general_rate():
    data = invoice_to_dict(_invoice())
    del data["lines"][0]["vat_rate"]  # KDV oranı yazılmadan kaydedilmiş eski kayıt
    restored = invoice_from_dict(data)
    assert restored.lines[0].vat_rate == VatRate(Decimal("0.20"))


def test_roundtrip_preserves_ettn():
    invoice = _invoice()  # onaylı
    invoice.send(ettn="ETTN-X")  # Sent + ETTN
    restored = invoice_from_dict(invoice_to_dict(invoice))
    assert restored.status is InvoiceStatus.Sent
    assert restored.ettn == "ETTN-X"
