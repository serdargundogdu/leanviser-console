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


def test_delete_removes_invoice():
    repo = SqliteInvoiceRepository(":memory:")
    repo.save(_invoice())
    repo.delete("INV-1")
    assert repo.get("INV-1") is None


def test_source_save_get_roundtrip():
    repo = SqliteInvoiceRepository(":memory:")
    assert repo.get_source("INV-1") is None
    repo.save_source("INV-1", {"invoice_id": "INV-1", "service_items": []})
    assert repo.get_source("INV-1") == {"invoice_id": "INV-1", "service_items": []}


def test_delete_also_removes_source():
    repo = SqliteInvoiceRepository(":memory:")
    repo.save(_invoice())
    repo.save_source("INV-1", {"invoice_id": "INV-1"})
    repo.delete("INV-1")
    assert repo.get_source("INV-1") is None


def test_next_invoice_sequence_increments_per_series_and_year():
    repo = SqliteInvoiceRepository(":memory:")
    assert repo.next_invoice_sequence("LVS", 2026) == 1
    assert repo.next_invoice_sequence("LVS", 2026) == 2
    assert repo.next_invoice_sequence("LVS", 2026) == 3
    # Farklı yıl ve farklı seri kendi sayaçlarına sahiptir.
    assert repo.next_invoice_sequence("LVS", 2027) == 1
    assert repo.next_invoice_sequence("ABC", 2026) == 1


def test_invoice_gib_number_and_ettn_roundtrip():
    repo = SqliteInvoiceRepository(":memory:")
    invoice = _invoice()
    invoice.gib_number = "LVS2026000000007"
    invoice.approve()
    invoice.send(ettn="ETTN-7")
    repo.save(invoice)
    loaded = repo.get("INV-1")
    assert loaded.gib_number == "LVS2026000000007"
    assert loaded.ettn == "ETTN-7"
