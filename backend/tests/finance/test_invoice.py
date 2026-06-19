"""Invoice aggregate testleri (framework-süz): kalem, toplam, durum makinesi, değişmezler."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.domain.invoice import (
    Invoice,
    InvoiceLine,
    InvoiceStateError,
    InvoiceStatus,
)
from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money


def _try(amount: str) -> Money:
    return Money(Decimal(amount), Currency.TRY)


def _invoice() -> Invoice:
    return Invoice(
        id="INV-1",
        customer_company="ACME",
        currency=Currency.TRY,
        issue_date=date(2026, 6, 19),
    )


def _service_line() -> InvoiceLine:
    # FX birim-önce sonucu: birim 35.838,08 TRY × 16 gün
    return InvoiceLine(
        description="Danışmanlık hizmet bedeli",
        unit_price=_try("35838.08"),
        quantity=Decimal("16"),
    )


def _expense_line() -> InvoiceLine:
    return InvoiceLine(
        description="Masraf: Akaryakıt (net)",
        unit_price=_try("100.00"),
        quantity=Decimal("1"),
    )


def test_new_invoice_starts_as_draft_and_empty():
    invoice = _invoice()
    assert invoice.status is InvoiceStatus.Draft
    assert invoice.lines == ()
    assert invoice.total() == _try("0.00")


def test_line_total_is_unit_price_times_quantity():
    assert _service_line().line_total() == _try("573409.28")
    assert _expense_line().line_total() == _try("100.00")


def test_total_sums_lines():
    invoice = _invoice()
    invoice.add_line(_service_line())
    invoice.add_line(_expense_line())
    assert invoice.total() == _try("573509.28")
    assert len(invoice.lines) == 2


def test_line_currency_must_match_invoice():
    invoice = _invoice()
    eur_line = InvoiceLine(
        description="EUR kalem",
        unit_price=Money(Decimal("10.00"), Currency.EUR),
        quantity=Decimal("1"),
    )
    with pytest.raises(CurrencyMismatchError):
        invoice.add_line(eur_line)


def test_lines_view_is_a_snapshot():
    invoice = _invoice()
    invoice.add_line(_expense_line())
    snapshot = invoice.lines
    invoice.add_line(_service_line())
    assert len(snapshot) == 1
    assert len(invoice.lines) == 2


def test_invalid_line_rejected():
    with pytest.raises(ValueError):
        InvoiceLine(description="x", unit_price=_try("10.00"), quantity=Decimal("0"))
    with pytest.raises(ValueError):
        InvoiceLine(description="x", unit_price=_try("0.00"), quantity=Decimal("1"))


def test_status_machine_draft_to_approved_to_sent():
    invoice = _invoice()
    invoice.add_line(_expense_line())
    invoice.approve()
    assert invoice.status is InvoiceStatus.Approved
    invoice.send()
    assert invoice.status is InvoiceStatus.Sent


def test_cannot_approve_empty_invoice():
    invoice = _invoice()
    with pytest.raises(InvoiceStateError):
        invoice.approve()


def test_cannot_add_line_after_approval():
    invoice = _invoice()
    invoice.add_line(_expense_line())
    invoice.approve()
    with pytest.raises(InvoiceStateError):
        invoice.add_line(_service_line())


def test_cannot_send_before_approval():
    invoice = _invoice()
    invoice.add_line(_expense_line())
    with pytest.raises(InvoiceStateError):
        invoice.send()


def test_cannot_approve_twice():
    invoice = _invoice()
    invoice.add_line(_expense_line())
    invoice.approve()
    with pytest.raises(InvoiceStateError):
        invoice.approve()


def test_cannot_send_twice():
    invoice = _invoice()
    invoice.add_line(_expense_line())
    invoice.approve()
    invoice.send()
    with pytest.raises(InvoiceStateError):
        invoice.send()


def test_identity_based_equality():
    a = _invoice()
    b = _invoice()
    assert a == b
    assert hash(a) == hash(b)
    c = Invoice(
        id="INV-2",
        customer_company="ACME",
        currency=Currency.TRY,
        issue_date=date(2026, 6, 19),
    )
    assert a != c
