"""'Fatura derleme' use case'i (application katmanı).

Angajman girdisinden (hizmet kalemleri + masraflar) bir Invoice (Draft) derler.
Döviz hizmet kalemleri, enjekte edilen ExchangeRateProvider port'undan çekilen
kurla ve birim-önce kuralıyla TRY'ye çevrilir; masraflar fatura para biriminde
olmalıdır. HTTP/DB bilmez — port'a bağımlıdır, bağımlılık içe akar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.domain.expense import Expense
from app.modules.finance.domain.fee_calculation import FeeCalculation
from app.modules.finance.domain.invoice import Invoice, InvoiceLine
from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money


@dataclass(frozen=True)
class ServiceItem:
    """Hizmet kalemi girdisi: günlük ücret × gün sayısı (consultantDays)."""

    description: str
    daily_rate: Money
    days: Decimal


@dataclass(frozen=True)
class CompileInvoiceCommand:
    """Fatura derleme girdisi. currency pratikte TRY'dir."""

    invoice_id: str
    customer_company: str
    issue_date: date
    currency: Currency
    service_items: tuple[ServiceItem, ...] = ()
    expenses: tuple[Expense, ...] = ()


class CompileInvoice:
    """Angajman girdisinden Invoice (Draft) üreten use case.

    FX tarihi olarak faturanın issue_date'i kullanılır. Onay/gönderim çağıranın
    sorumluluğundadır (Invoice.approve()/send()).
    """

    def __init__(self, exchange_rate_provider: ExchangeRateProvider) -> None:
        self._rates = exchange_rate_provider

    def execute(self, command: CompileInvoiceCommand) -> Invoice:
        invoice = Invoice(
            id=command.invoice_id,
            customer_company=command.customer_company,
            currency=command.currency,
            issue_date=command.issue_date,
        )
        for item in command.service_items:
            invoice.add_line(self._service_line(item, command.currency, command.issue_date))
        for expense in command.expenses:
            invoice.add_line(self._expense_line(expense, command.currency))
        return invoice

    def _service_line(self, item: ServiceItem, currency: Currency, as_of: date) -> InvoiceLine:
        if item.daily_rate.currency is currency:
            # aynı para birimi: doğrudan günlük ücret
            return InvoiceLine(
                description=item.description, unit_price=item.daily_rate, quantity=item.days
            )
        # döviz: TCMB kuruyla birim-önce TRY'ye çevrilir; kullanılan kur açıklamaya yazılır
        fx = self._rates.get_rate(item.daily_rate.currency, currency, as_of)
        unit_price = FeeCalculation.to_try(item.daily_rate, fx)
        description = (
            f"{item.description} ({item.daily_rate.currency.code} kuru "
            f"{fx.as_of:%d.%m.%Y} · {fx.rate})"
        )
        return InvoiceLine(description=description, unit_price=unit_price, quantity=item.days)

    @staticmethod
    def _expense_line(expense: Expense, currency: Currency) -> InvoiceLine:
        net = expense.net_amount()
        if net.currency is not currency:
            raise CurrencyMismatchError(f"Masraf {net.currency.code}, fatura {currency.code}")
        return InvoiceLine(
            description=f"Masraf: {expense.type.value}",
            unit_price=net,
            quantity=Decimal(1),
        )
