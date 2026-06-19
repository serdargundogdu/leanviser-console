"""SqliteInvoiceRepository testleri — in-memory DB; ağsız ve izole."""

from datetime import date
from decimal import Decimal

from app.modules.finance.adapters.sqlite_invoice_repository import SqliteInvoiceRepository
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
    return invoice


def test_save_and_get_roundtrip():
    repo = SqliteInvoiceRepository(":memory:")
    repo.save(_invoice())
    loaded = repo.get("INV-1")
    assert loaded is not None
    assert loaded.id == "INV-1"
    assert loaded.customer_company == "ACME"
    assert loaded.currency is Currency.TRY
    assert loaded.status is InvoiceStatus.Draft
    assert loaded.total() == Money(Decimal("573409.28"), Currency.TRY)
    assert len(loaded.lines) == 1


def test_get_missing_returns_none():
    repo = SqliteInvoiceRepository(":memory:")
    assert repo.get("YOK") is None


def test_save_is_idempotent_upsert():
    repo = SqliteInvoiceRepository(":memory:")
    repo.save(_invoice())
    repo.save(_invoice())
    assert repo.get("INV-1") is not None


def test_reconstitutes_approved_invoice():
    repo = SqliteInvoiceRepository(":memory:")
    invoice = _invoice()
    invoice.approve()
    repo.save(invoice)
    loaded = repo.get("INV-1")
    assert loaded is not None
    assert loaded.status is InvoiceStatus.Approved


def test_list_all_returns_saved_invoices():
    repo = SqliteInvoiceRepository(":memory:")
    assert repo.list_all() == []
    repo.save(_invoice())
    invoices = repo.list_all()
    assert len(invoices) == 1
    assert invoices[0].id == "INV-1"
