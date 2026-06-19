"""PostgresInvoiceRepository entegrasyon testi.

Yalnız TEST_DATABASE_URL tanımlıyken çalışır; aksi hâlde tüm modül atlanır (CI
ağsız/yeşil kalır). DSN örneği: postgresql://user:pass@localhost:5432/leanviser_test
"""

import os
from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.adapters.postgres_invoice_repository import PostgresInvoiceRepository
from app.modules.finance.domain.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.modules.finance.domain.money import Currency, Money
from app.modules.finance.domain.vat import VatRate

_DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(_DSN is None, reason="TEST_DATABASE_URL tanımlı değil")


def _invoice(invoice_id: str) -> Invoice:
    invoice = Invoice(
        id=invoice_id,
        customer_company="ACME",
        currency=Currency.TRY,
        issue_date=date(2026, 6, 19),
    )
    invoice.add_line(
        InvoiceLine(
            description="Hizmet",
            unit_price=Money(Decimal("100.00"), Currency.TRY),
            quantity=Decimal("2"),
        )
    )
    return invoice


def test_save_get_list_roundtrip():
    repo = PostgresInvoiceRepository(_DSN)
    invoice = _invoice("INV-PG-1")
    invoice.approve()
    repo.save(invoice)
    loaded = repo.get("INV-PG-1")
    assert loaded is not None
    assert loaded.status is InvoiceStatus.Approved
    assert loaded.total() == Money(Decimal("200.00"), Currency.TRY)
    assert any(saved.id == "INV-PG-1" for saved in repo.list_all())


def test_get_missing_returns_none():
    repo = PostgresInvoiceRepository(_DSN)
    assert repo.get("INV-PG-MISSING") is None


def test_delete_removes_invoice():
    repo = PostgresInvoiceRepository(_DSN)
    repo.save(_invoice("INV-PG-DEL"))
    repo.delete("INV-PG-DEL")
    assert repo.get("INV-PG-DEL") is None


def test_source_roundtrip():
    repo = PostgresInvoiceRepository(_DSN)
    repo.save_source("INV-PG-SRC", {"invoice_id": "INV-PG-SRC", "service_items": []})
    assert repo.get_source("INV-PG-SRC") == {"invoice_id": "INV-PG-SRC", "service_items": []}


def test_next_invoice_sequence_is_monotonic_per_series():
    repo = PostgresInvoiceRepository(_DSN)
    a1 = repo.next_invoice_sequence("PGT", 2026)
    a2 = repo.next_invoice_sequence("PGT", 2026)
    b1 = repo.next_invoice_sequence("PGZ", 2099)  # ayrı (seri, yıl) -> bağımsız sayaç
    a3 = repo.next_invoice_sequence("PGT", 2026)
    assert a2 == a1 + 1
    assert a3 == a2 + 1
    assert b1 >= 1


def test_gib_number_ettn_and_per_line_vat_roundtrip():
    repo = PostgresInvoiceRepository(_DSN)
    invoice = _invoice("INV-PG-VAT")  # 1. kalem: net 200, KDV %20
    invoice.add_line(
        InvoiceLine(
            description="İkinci kalem",
            unit_price=Money(Decimal("50.00"), Currency.TRY),
            quantity=Decimal("1"),
            vat_rate=VatRate(Decimal("0.10")),
        )
    )
    invoice.gib_number = "LVS2026000000099"
    invoice.approve()
    invoice.send(ettn="ETTN-PG")
    repo.save(invoice)

    loaded = repo.get("INV-PG-VAT")
    assert loaded.status is InvoiceStatus.Sent
    assert loaded.gib_number == "LVS2026000000099"
    assert loaded.ettn == "ETTN-PG"
    assert loaded.lines[0].vat_rate == VatRate(Decimal("0.20"))
    assert loaded.lines[1].vat_rate == VatRate(Decimal("0.10"))
    assert loaded.vat_total() == Money(Decimal("45.00"), Currency.TRY)  # 40 + 5
