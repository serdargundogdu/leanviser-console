"""CompileInvoice use case testleri — sahte (stub) ExchangeRateProvider; ağsız."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.application.compile_invoice import (
    CompileInvoice,
    CompileInvoiceCommand,
    ServiceItem,
)
from app.modules.finance.domain.expense import Expense, ExpenseType
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.invoice import InvoiceStatus
from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money
from app.modules.finance.domain.vat import VatRate

AS_OF = date(2026, 6, 19)


class _StubRates:
    """Sabit kur döndüren, çağrıları kaydeden sahte ExchangeRateProvider."""

    def __init__(self, rate: Decimal) -> None:
        self._rate = rate
        self.calls: list[tuple[Currency, Currency, date]] = []

    def get_rate(self, base: Currency, quote: Currency, as_of: date) -> ExchangeRate:
        self.calls.append((base, quote, as_of))
        return ExchangeRate(base=base, rate=self._rate, as_of=as_of, quote=quote)


def _try(amount: str) -> Money:
    return Money(Decimal(amount), Currency.TRY)


def _command(**overrides) -> CompileInvoiceCommand:
    return CompileInvoiceCommand(
        invoice_id="INV-1",
        customer_company="ACME",
        issue_date=AS_OF,
        currency=Currency.TRY,
        **overrides,
    )


def _expense(gross: Money) -> Expense:
    return Expense(
        id="E-1",
        gross=gross,
        vat_rate=VatRate(Decimal("0.20")),
        type=ExpenseType.Fuel,
        date=AS_OF,
        company="ACME",
    )


def test_fx_service_line_is_unit_first():
    rates = _StubRates(Decimal("47.7841"))
    command = _command(
        service_items=(
            ServiceItem(
                description="Danışmanlık",
                daily_rate=Money(Decimal("750.00"), Currency.EUR),
                days=Decimal("16"),
            ),
        )
    )
    invoice = CompileInvoice(rates).execute(command)
    assert invoice.status is InvoiceStatus.Draft
    assert invoice.total() == _try("573409.28")
    assert rates.calls == [(Currency.EUR, Currency.TRY, AS_OF)]


def test_same_currency_service_line_skips_fx():
    rates = _StubRates(Decimal("47.7841"))
    command = _command(
        service_items=(
            ServiceItem(
                description="Danışmanlık (TRY)", daily_rate=_try("1000.00"), days=Decimal("5")
            ),
        )
    )
    invoice = CompileInvoice(rates).execute(command)
    assert invoice.total() == _try("5000.00")
    assert rates.calls == []


def test_expense_net_line():
    rates = _StubRates(Decimal("47.7841"))
    command = _command(expenses=(_expense(_try("120.00")),))
    invoice = CompileInvoice(rates).execute(command)
    assert invoice.total() == _try("100.00")


def test_mixed_invoice_total_and_lines():
    rates = _StubRates(Decimal("47.7841"))
    command = _command(
        service_items=(
            ServiceItem(
                description="Danışmanlık",
                daily_rate=Money(Decimal("750.00"), Currency.EUR),
                days=Decimal("16"),
            ),
        ),
        expenses=(_expense(_try("120.00")),),
    )
    invoice = CompileInvoice(rates).execute(command)
    assert invoice.total() == _try("573509.28")
    assert len(invoice.lines) == 2


def test_foreign_expense_rejected():
    rates = _StubRates(Decimal("47.7841"))
    command = _command(expenses=(_expense(Money(Decimal("120.00"), Currency.EUR)),))
    with pytest.raises(CurrencyMismatchError):
        CompileInvoice(rates).execute(command)
