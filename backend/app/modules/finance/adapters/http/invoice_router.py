"""Finance HTTP adapter (driving): fatura derleme uç noktası.

FastAPI router'ı. HTTP DTO'ları (Pydantic) burada yaşar ve application/domain
modellerine map'lenir; çekirdek HTTP bilmez (hexagonal: driving adapter).
Not: Bu dosya Pydantic kullandığı için PEP 563 (future annotations) bilinçli
olarak kullanılmaz — Pydantic alan tiplerini kuruluşta gerçek tip olarak ister.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.modules.finance.adapters.http.dependencies import (
    get_exchange_rate_provider,
    get_invoice_repository,
)
from app.modules.finance.application.compile_invoice import (
    CompileInvoice,
    CompileInvoiceCommand,
    ServiceItem,
)
from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.application.invoice_repository import InvoiceRepository
from app.modules.finance.domain.expense import Expense, ExpenseType
from app.modules.finance.domain.invoice import Invoice
from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money
from app.modules.finance.domain.vat import VatRate

router = APIRouter(prefix="/finance", tags=["finance"])


class ServiceItemIn(BaseModel):
    """Hizmet kalemi girdisi. Tutarlar kesinlik için string olarak gönderilir."""

    description: str
    daily_rate: Decimal
    currency: str
    days: Decimal


class ExpenseIn(BaseModel):
    """Masraf girdisi."""

    type: str
    gross: Decimal
    vat_rate: Decimal
    currency: str = "TRY"


class CompileInvoiceRequest(BaseModel):
    """Fatura derleme isteği."""

    invoice_id: str
    customer_company: str
    issue_date: date
    currency: str = "TRY"
    service_items: list[ServiceItemIn] = []
    expenses: list[ExpenseIn] = []


class InvoiceLineOut(BaseModel):
    """Yanıt kalemi (tutarlar string)."""

    description: str
    unit_price: str
    quantity: str
    line_total: str


class InvoiceResponse(BaseModel):
    """Derlenmiş fatura yanıtı."""

    id: str
    status: str
    currency: str
    customer_company: str
    issue_date: date
    lines: list[InvoiceLineOut]
    total: str


def _currency(code: str) -> Currency:
    try:
        return Currency[code]
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Geçersiz para birimi: {code}") from None


def _expense_type(name: str) -> ExpenseType:
    try:
        return ExpenseType[name]
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Geçersiz masraf türü: {name}") from None


def _to_command(request: CompileInvoiceRequest) -> CompileInvoiceCommand:
    service_items = tuple(
        ServiceItem(
            description=item.description,
            daily_rate=Money(item.daily_rate, _currency(item.currency)),
            days=item.days,
        )
        for item in request.service_items
    )
    expenses = tuple(
        Expense(
            id=f"E-{index}",
            gross=Money(expense.gross, _currency(expense.currency)),
            vat_rate=VatRate(expense.vat_rate),
            type=_expense_type(expense.type),
            date=request.issue_date,
            company=request.customer_company,
        )
        for index, expense in enumerate(request.expenses, start=1)
    )
    return CompileInvoiceCommand(
        invoice_id=request.invoice_id,
        customer_company=request.customer_company,
        issue_date=request.issue_date,
        currency=_currency(request.currency),
        service_items=service_items,
        expenses=expenses,
    )


def _to_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        status=invoice.status.value,
        currency=invoice.currency.code,
        customer_company=invoice.customer_company,
        issue_date=invoice.issue_date,
        lines=[
            InvoiceLineOut(
                description=line.description,
                unit_price=str(line.unit_price.amount),
                quantity=str(line.quantity),
                line_total=str(line.line_total().amount),
            )
            for line in invoice.lines
        ],
        total=str(invoice.total().amount),
    )


@router.post("/invoices", response_model=InvoiceResponse)
def compile_invoice(
    request: CompileInvoiceRequest,
    provider: Annotated[ExchangeRateProvider, Depends(get_exchange_rate_provider)],
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    """Angajman girdisinden Draft fatura derler, kaydeder ve döner."""
    try:
        command = _to_command(request)
        invoice = CompileInvoice(provider).execute(command)
    except (ValueError, CurrencyMismatchError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    repository.save(invoice)
    return _to_response(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    """Kayıtlı faturayı id ile döndürür; yoksa 404."""
    invoice = repository.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadı: {invoice_id}")
    return _to_response(invoice)
