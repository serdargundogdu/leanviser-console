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
